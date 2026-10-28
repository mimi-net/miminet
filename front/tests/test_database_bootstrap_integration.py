"""Проверки инициализации настоящей PostgreSQL-схемы до и после рефакторинга."""

from datetime import datetime, timezone
import logging
import os
import uuid

import pytest
from flask import Flask
from psycopg2 import OperationalError
from sqlalchemy import inspect, text
from sqlalchemy.engine import make_url

from app import app as configured_app
from database_bootstrap import ensure_db_exists, init_db
from miminet_model import SimulateLog, db


@pytest.fixture
def bootstrap_postgres(monkeypatch, request):
    """Изолированная пустая схема: исходные модели и настоящий драйвер PostgreSQL."""
    uri = os.getenv("MIMINET_TEST_POSTGRES_URL")
    if not uri:
        pytest.skip("Нужен MIMINET_TEST_POSTGRES_URL отдельной тестовой БД")
    schema = f"miminet_test_{uuid.uuid4().hex}"
    application = Flask("database-bootstrap-regression")
    application.config.update(
        SQLALCHEMY_DATABASE_URI=uri,
        SQLALCHEMY_ENGINE_OPTIONS={
            "connect_args": {"options": f"-csearch_path={schema}"}
        },
    )
    monkeypatch.setenv("MODE", "dev")
    monkeypatch.setenv("SQLALCHEMY_DATABASE_URI", uri)
    db.init_app(application)
    with application.app_context():
        engine = db.engine

        def cleanup():
            try:
                with engine.begin() as connection:
                    connection.execute(
                        text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
                    )
            finally:
                engine.dispose()

        request.addfinalizer(cleanup)
        with engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        yield application


def test_clean_postgres_bootstrap_creates_registered_schema(bootstrap_postgres):
    """Чистая схема получает все зарегистрированные таблицы приложения."""
    assert inspect(db.engine).get_table_names() == []
    assert configured_app.extensions["sqlalchemy"] is db
    assert bootstrap_postgres.extensions["sqlalchemy"] is db

    init_db(bootstrap_postgres)

    assert set(inspect(db.engine).get_table_names()) == set(db.metadata.tables)
    assert SimulateLog.query.count() == 0


@pytest.mark.parametrize("mode", ["dev", "prod"])
def test_existing_postgres_schema_repairs_only_pending_logs(
    bootstrap_postgres, monkeypatch, mode
):
    """Повторный запуск сохраняет таблицы и ранее завершённые журналы."""
    init_db(bootstrap_postgres)
    original_tables = set(inspect(db.engine).get_table_names())
    completed_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
    db.session.add_all(
        [
            SimulateLog(id=1, author_id=42, network_guid="pending", ready=False),
            SimulateLog(
                id=2,
                author_id=42,
                network_guid="completed",
                ready=True,
                simulate_end=completed_at,
            ),
        ]
    )
    db.session.commit()
    monkeypatch.setenv("MODE", mode)

    init_db(bootstrap_postgres)
    db.session.remove()
    rows = SimulateLog.query.order_by(SimulateLog.id).all()
    assert [row.ready for row in rows] == [True, True]
    assert rows[0].simulate_end is not None
    assert rows[1].simulate_end == completed_at
    first_result = [(row.id, row.network_guid, row.simulate_end) for row in rows]

    init_db(bootstrap_postgres)
    db.session.remove()
    rows = SimulateLog.query.order_by(SimulateLog.id).all()
    assert [
        (row.id, row.network_guid, row.simulate_end) for row in rows
    ] == first_result
    assert set(inspect(db.engine).get_table_names()) == original_tables


@pytest.mark.parametrize("mode", ["dev", "prod"])
def test_provisioning_connects_to_existing_test_database(bootstrap_postgres, mode):
    """Подготовка доступной БД проверяется настоящим подключением без создания базы."""
    target = make_url(bootstrap_postgres.config["SQLALCHEMY_DATABASE_URI"])
    assert (
        ensure_db_exists(
            target.host,
            target.username,
            target.password,
            target.database,
            port=target.port or 5432,
            mode=mode,
        )
        is True
    )


def test_prod_provisioning_does_not_create_missing_database(bootstrap_postgres):
    """В рабочем режиме отсутствующая БД остаётся отсутствующей после ошибки."""
    target = make_url(bootstrap_postgres.config["SQLALCHEMY_DATABASE_URI"])
    missing = f"miminet_missing_{uuid.uuid4().hex}"

    with pytest.raises(OperationalError):
        ensure_db_exists(
            target.host,
            target.username,
            target.password,
            missing,
            port=target.port or 5432,
            mode="prod",
        )

    with db.engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": missing},
            ).first()
            is None
        )


@pytest.mark.parametrize("mode", ["dev", "prod"])
def test_failed_postgres_repair_logs_safe_traceback_and_sqlstate(
    bootstrap_postgres, monkeypatch, mode, caplog
):
    """Реальная ошибка CHECK диагностируется без вывода приватной строки сети."""
    init_db(bootstrap_postgres)
    secret = uuid.uuid4().hex
    db.session.add(
        SimulateLog(
            id=1, author_id=42, network_guid="pending", ready=False, network=secret
        )
    )
    db.session.commit()
    with db.engine.begin() as connection:
        connection.execute(
            text(
                "ALTER TABLE simulate_log ADD CONSTRAINT test_block_ready CHECK (NOT ready)"
            )
        )
    monkeypatch.setenv("MODE", mode)
    caplog.clear()

    with caplog.at_level(logging.ERROR, logger="miminet_model"):
        assert init_db(bootstrap_postgres) is None

    errors = [
        r
        for r in caplog.records
        if r.name == "miminet_model" and r.levelno == logging.ERROR
    ]
    assert len(errors) == 1
    assert errors[0].exc_info is not None
    assert errors[0].error_type == "IntegrityError"
    assert errors[0].sqlstate == "23514"
    assert errors[0].bootstrap_mode == mode
    assert "Traceback" in caplog.text
    assert secret not in caplog.text
    assert "[SQL:" not in caplog.text
    db.session.remove()
    row = db.session.get(SimulateLog, 1)
    assert row.ready is False
    assert row.network == secret
