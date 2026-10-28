"""Общий HTTP/ORM-стенд с изолированными SQLite и PostgreSQL."""

import os
from types import SimpleNamespace
import uuid

import pytest
from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token
from sqlalchemy import BigInteger, Integer, MetaData, event, text

import miminet_simulation
from app import app as configured_app
from miminet_model import Network, Simulate, SimulateLog, User, db


@pytest.fixture(params=["sqlite", "postgres"])
def simulation_http(tmp_path, mocker, request):
    """Каждый сценарий выполняется на SQLite и на отдельной схеме PostgreSQL."""
    postgres = request.param == "postgres"
    postgres_uri = os.getenv("MIMINET_TEST_POSTGRES_URL")
    if postgres and not postgres_uri:
        pytest.skip("Для PostgreSQL задайте MIMINET_TEST_POSTGRES_URL тестового стенда")
    schema = f"miminet_test_{uuid.uuid4().hex}" if postgres else None
    application = Flask("simulation-regression")
    application.config.update(
        TESTING=True,
        SECRET_KEY="regression-session-secret",
        JWT_SECRET_KEY="regression-jwt-secret-at-least-32-characters",
        JWT_TOKEN_LOCATION=["headers"],
        SQLALCHEMY_DATABASE_URI=(
            postgres_uri
            if postgres
            else f"sqlite:///{(tmp_path / 'simulation.sqlite').as_posix()}"
        ),
    )
    if postgres:
        application.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "connect_args": {"options": f"-csearch_path={schema}"}
        }
    JWTManager(application)
    db.init_app(application)
    application.add_url_rule("/home", endpoint="home", view_func=lambda: "home")
    # Берём обработчики и методы из настоящего приложения, чтобы стенд
    # не разрешал запросы, запрещённые реальной конфигурацией маршрутов.
    for path in (
        "/run_simulation",
        "/check_simulation",
        "/delete_network",
        "/network/update_network_config",
        "/post_network_nodes",
        "/post_nodes_edges",
        "/move_network_nodes",
        "/network/copy_network",
    ):
        rule = next(
            rule for rule in configured_app.url_map.iter_rules() if rule.rule == path
        )
        application.add_url_rule(
            path,
            view_func=configured_app.view_functions[rule.endpoint],
            methods=sorted(rule.methods - {"HEAD", "OPTIONS"}),
        )
    send_task = mocker.patch.object(miminet_simulation.app, "send_task")

    with application.app_context():
        engine = db.engine

        def cleanup_database():
            # Финализатор запускается и при ошибке подготовки, до yield.
            try:
                if postgres:
                    with engine.begin() as connection:
                        connection.execute(
                            text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
                        )
            finally:
                engine.dispose()

        request.addfinalizer(cleanup_database)
        if postgres:
            with db.engine.begin() as connection:
                connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        else:
            # SQLite по умолчанию не проверяет внешние ключи: включаем их,
            # чтобы тесты удаления действительно обнаруживали нарушения связей.
            @event.listens_for(db.engine, "connect")
            def enable_foreign_keys(connection, _record):
                cursor = connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

        # В SQLite автоинкремент требует INTEGER PRIMARY KEY. Меняем только
        # копию DDL для тестовой БД; исходные ORM-модели остаются неизменными.
        metadata = MetaData()
        for model in (User, Network, Simulate, SimulateLog):
            table = model.__table__.to_metadata(metadata)
            for column in table.primary_key:
                if not postgres and isinstance(column.type, BigInteger):
                    column.type = Integer()
        metadata.create_all(db.engine)
        db.session.add_all([User(id=1, nick="owner"), User(id=2, nick="other")])
        db.session.flush()
        db.session.add_all(
            [
                Network(id=10, author_id=1, guid="owner-network"),
                Network(id=20, author_id=2, guid="other-network"),
            ]
        )
        db.session.flush()
        db.session.add_all(
            [
                Simulate(id=101, network_id=10, ready=False, packets="owner-packets"),
                Simulate(id=202, network_id=20, ready=True, packets="other-packets"),
            ]
        )
        db.session.commit()
        headers = {"Authorization": f"Bearer {create_access_token(identity='1')}"}
        try:
            yield SimpleNamespace(
                app=application,
                client=application.test_client(),
                headers=headers,
                send_task=send_task,
            )
        finally:
            db.session.remove()


def persisted_state():
    """Перечитываем строки из БД вместо проверки кешированных ORM-объектов."""
    db.session.remove()
    return (
        [
            (n.id, n.author_id, n.title, n.description, n.network)
            for n in Network.query.order_by(Network.id)
        ],
        [
            (s.id, s.network_id, s.ready, s.packets)
            for s in Simulate.query.order_by(Simulate.id)
        ],
        SimulateLog.query.count(),
    )
