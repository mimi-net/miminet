from datetime import datetime
from unittest.mock import MagicMock

import pytest

# Каталог src добавляется в путь импорта в conftest.py.
from app import get_database_uri
from flask import Flask
from database_bootstrap import ensure_db_exists, init_db
from miminet_model import SimulateLog, User, db
from psycopg2 import OperationalError
from sqlalchemy import text


class TestConfigDB:
    """Проверки конфигурации подключения и инициализации базы данных."""

    def test_get_database_uri_dev(self, mock_env_dev):
        """В режиме разработки используется локальный PostgreSQL без TLS."""
        uri = get_database_uri("dev")
        assert "postgresql+psycopg2://" in uri
        assert "@localhost/" in uri
        assert "sslmode" not in uri

    def test_get_database_uri_prod(self, mock_env_prod):
        """В рабочем режиме URI содержит параметры защищённого подключения."""
        uri = get_database_uri("prod")
        assert "postgresql+psycopg2://" in uri
        assert "rc1a-test" in uri
        assert "sslmode=verify-full" in uri
        assert "sslrootcert=/tmp/root.crt" in uri

    def test_get_database_uri_prod_missing_creds(self, mock_env_prod, monkeypatch):
        """Отсутствие пароля рабочего подключения обнаруживается до запуска."""
        monkeypatch.delenv("YANDEX_POSTGRES_PASSWORD")
        with pytest.raises(
            ValueError, match="Missing Yandex Cloud PostgreSQL credentials"
        ):
            get_database_uri("prod")

    def test_ensure_db_exists_prod_success(self, mock_env_prod, mock_psycopg2):
        """Доступная рабочая БД не требует подключения к системной базе."""
        mock_connect, _ = mock_psycopg2

        res = ensure_db_exists("host", "u", "p", "db", mode="prod", sslmode="require")

        assert res is True
        mock_connect.assert_called_once()
        assert mock_connect.call_args[1]["dbname"] == "db"

    def test_ensure_db_exists_prod_failure(self, mock_env_prod, mock_psycopg2):
        """Ошибка рабочего подключения передаётся вызывающему коду."""
        mock_connect, _ = mock_psycopg2
        mock_connect.side_effect = OperationalError("Connection failed")

        with pytest.raises(OperationalError):
            ensure_db_exists("host", "u", "p", "db", mode="prod")

        # В рабочем режиме запрещён автоматический переход к системной БД.
        assert mock_connect.call_count == 1

    def test_ensure_db_exists_dev_create(self, mock_env_dev, mock_psycopg2):
        """В режиме разработки отсутствующая база создаётся автоматически."""
        mock_connect, mock_cursor = mock_psycopg2

        # Первое подключение к целевой базе завершается ошибкой;
        # второе подключение к системной базе позволяет создать целевую.
        success_conn = MagicMock()
        success_conn.cursor.return_value.__enter__.return_value = mock_cursor
        success_conn.__enter__.return_value = success_conn

        mock_connect.side_effect = [OperationalError("DB missing"), success_conn]
        mock_cursor.fetchone.return_value = None  # База отсутствует в каталоге.

        ensure_db_exists("h", "u", "p", "new_db", mode="dev")

        assert mock_connect.call_count == 2
        # Повторное подключение должно использовать системную базу postgres.
        assert mock_connect.call_args[1]["dbname"] == "postgres"
        # Проверяем запрос создания, а не только число подключений.
        mock_cursor.execute.assert_any_call("CREATE DATABASE new_db")

    def test_init_db_dev(self, mock_env_dev, mocker, mock_sqlalchemy_inspect, mock_db):
        """При отсутствии таблиц инициализатор создаёт схему."""
        mocker.patch("database_bootstrap.ensure_db_exists", return_value=True)

        # Инспектор сообщает, что таблица пользователей ещё не создана.
        mock_sqlalchemy_inspect.has_table.return_value = False

        app_mock = MagicMock()

        init_db(app_mock)

        mock_db.create_all.assert_called_once()
        mock_sqlalchemy_inspect.has_table.assert_called_with("user")
        # Список начальных пользователей сейчас пуст: добавлять записи не нужно.


class TestBootstrapRegression:
    """Фиксируем решения при запуске перед отделением инициализации от моделей.

    Здесь подключения к БД подменены. Эти проверки не подтверждают
    корректность DDL и транзакций настоящего PostgreSQL.
    """

    @pytest.mark.parametrize("mode", ["dev", "prod"])
    @pytest.mark.parametrize("override", [None, "", "sqlite:///:memory:"])
    def test_uri_override_controls_provisioning(
        self, mode, override, monkeypatch, mocker, mock_db, mock_sqlalchemy_inspect
    ):
        """Явный URI исключает подготовку другой БД из переменных режима."""
        monkeypatch.setenv("MODE", mode)
        values = {
            "POSTGRES_HOST": "dev.invalid",
            "POSTGRES_DEFAULT_USER": "dev-user",
            "POSTGRES_DEFAULT_PASSWORD": "test-only",
            "POSTGRES_DATABASE_NAME": "dev-db",
            "YANDEX_POSTGRES_HOST": "prod.invalid",
            "YANDEX_POSTGRES_USER": "prod-user",
            "YANDEX_POSTGRES_PASSWORD": "test-only",
            "YANDEX_POSTGRES_DB": "prod-db",
            "YANDEX_POSTGRES_PORT": "6543",
            "YANDEX_POSTGRES_SSLMODE": "verify-full",
            "YANDEX_POSTGRES_SSLROOTCERT": "/test/root.crt",
        }
        for key, value in values.items():
            monkeypatch.setenv(key, value)
        if override is None:
            monkeypatch.delenv("SQLALCHEMY_DATABASE_URI", raising=False)
        else:
            monkeypatch.setenv("SQLALCHEMY_DATABASE_URI", override)
        provision = mocker.patch("database_bootstrap.ensure_db_exists")
        mock_sqlalchemy_inspect.has_table.return_value = False

        init_db(MagicMock())

        if override:
            provision.assert_not_called()
        elif mode == "dev":
            provision.assert_called_once_with(
                "dev.invalid",
                "dev-user",
                "test-only",
                "dev-db",
                port=5432,
                sslmode=None,
                sslrootcert=None,
                mode="dev",
            )
        else:
            provision.assert_called_once_with(
                "prod.invalid",
                "prod-user",
                "test-only",
                "prod-db",
                port=6543,
                sslmode="verify-full",
                sslrootcert="/test/root.crt",
                mode="prod",
            )
        mock_db.create_all.assert_called_once()

    def test_existing_schema_repairs_unfinished_simulations_without_recreation(
        self, mock_env_dev, monkeypatch, mocker, mock_db, mock_sqlalchemy_inspect
    ):
        """Готовая схема сохраняется, а незавершённые журналы обновляются."""
        monkeypatch.setenv("SQLALCHEMY_DATABASE_URI", "sqlite:///:memory:")
        mock_sqlalchemy_inspect.has_table.return_value = True
        log_model = mocker.patch("database_bootstrap.SimulateLog")

        init_db(MagicMock())

        mock_db.create_all.assert_not_called()
        log_model.query.filter.return_value.update.assert_called_once_with(
            {"ready": True}
        )
        mock_db.session.commit.assert_called_once()

    @pytest.mark.parametrize("override", ["", "sqlite:///:memory:"])
    def test_invalid_mode_is_rejected_even_with_uri_override(
        self, override, monkeypatch, mocker, mock_db
    ):
        """Неизвестный режим отклоняется даже при явно заданном URI."""
        monkeypatch.setenv("MODE", "unsupported")
        monkeypatch.setenv("SQLALCHEMY_DATABASE_URI", override)
        provision = mocker.patch("database_bootstrap.ensure_db_exists")
        inspector = mocker.patch("database_bootstrap.inspect")

        with pytest.raises(ValueError, match="Unknown MODE: unsupported"):
            init_db(MagicMock())

        provision.assert_not_called()
        inspector.assert_not_called()
        mock_db.create_all.assert_not_called()

    def test_provisioning_failure_stops_before_schema_changes(
        self, mock_env_dev, monkeypatch, mocker, mock_db
    ):
        """Ошибка подготовки БД не должна приводить к изменению схемы."""
        monkeypatch.delenv("SQLALCHEMY_DATABASE_URI", raising=False)
        failure = OperationalError("test provisioning failure")
        mocker.patch("database_bootstrap.ensure_db_exists", side_effect=failure)
        inspector = mocker.patch("database_bootstrap.inspect")

        with pytest.raises(OperationalError) as caught:
            init_db(MagicMock())

        assert caught.value is failure
        inspector.assert_not_called()
        mock_db.create_all.assert_not_called()
        mock_db.session.commit.assert_not_called()


class TestDatabaseURIRegression:
    """Граничные случаи конфигурации, которые нельзя потерять при переносе кода."""

    @pytest.mark.parametrize(
        "key",
        ["YANDEX_POSTGRES_HOST", "YANDEX_POSTGRES_USER", "YANDEX_POSTGRES_PASSWORD"],
    )
    @pytest.mark.parametrize("value", [None, ""])
    def test_prod_rejects_missing_or_empty_credentials(
        self, key, value, mock_env_prod, monkeypatch
    ):
        """Каждый обязательный параметр проверяется и на отсутствие, и на пустоту."""
        if value is None:
            monkeypatch.delenv(key)
        else:
            monkeypatch.setenv(key, value)

        with pytest.raises(
            ValueError, match="Missing Yandex Cloud PostgreSQL credentials"
        ):
            get_database_uri("prod")

    def test_prod_uri_uses_default_tls_and_port(self, mock_env_prod, monkeypatch):
        """Без необязательных настроек сохраняются рабочие значения TLS и порта."""
        for key in (
            "YANDEX_POSTGRES_PORT",
            "YANDEX_POSTGRES_SSLMODE",
            "YANDEX_POSTGRES_SSLROOTCERT",
        ):
            monkeypatch.delenv(key)

        assert get_database_uri("prod") == (
            "postgresql+psycopg2://prod_user:prod_pass@rc1a-test.mdb.yandexcloud.net:6432/"
            "miminet_prod?sslmode=verify-full&sslrootcert=/app/.postgresql/root.crt"
        )

    @pytest.mark.parametrize("mode", ["", "test", "PROD"])
    def test_unknown_mode_is_not_silently_treated_as_dev(self, mode):
        """Опечатка в режиме не должна незаметно включить конфигурацию разработки."""
        with pytest.raises(ValueError, match="Unknown MODE"):
            get_database_uri(mode)


class TestProvisioningRegression:
    """Подключения и SQL подменены: проверяем контракт подготовки базы."""

    @pytest.mark.parametrize(
        "sslmode, sslrootcert",
        [
            (None, None),
            ("require", None),
            (None, "/test/ca.crt"),
            ("verify-full", "/test/ca.crt"),
        ],
    )
    def test_connection_options_are_forwarded(
        self, sslmode, sslrootcert, mock_psycopg2
    ):
        """Необязательные TLS-параметры передаются только при наличии значения."""
        connect, _ = mock_psycopg2
        expected = {
            "host": "database.invalid",
            "user": "test-user",
            "password": "test-only",
            "dbname": "practice",
            "port": 6543,
        }
        if sslmode:
            expected["sslmode"] = sslmode
        if sslrootcert:
            expected["sslrootcert"] = sslrootcert

        assert (
            ensure_db_exists(
                "database.invalid",
                "test-user",
                "test-only",
                "practice",
                port=6543,
                sslmode=sslmode,
                sslrootcert=sslrootcert,
            )
            is True
        )

        connect.assert_called_once_with(**expected)
        connect.return_value.__enter__.return_value.cursor.assert_not_called()

    def test_fallback_does_not_recreate_existing_database(self, mock_psycopg2, caplog):
        """Сбой первого подключения не означает, что существующую БД надо создавать."""
        connect, cursor = mock_psycopg2
        connection = MagicMock()
        connection.__enter__.return_value = connection
        connection.cursor.return_value.__enter__.return_value = cursor
        connect.side_effect = [OperationalError("unavailable"), connection]
        cursor.fetchone.return_value = (1,)

        assert ensure_db_exists("host", "user", "test-only", "practice") is True

        cursor.execute.assert_called_once_with(
            "SELECT 1 FROM pg_database WHERE datname = %s", ("practice",)
        )
        assert connection.autocommit is True
        assert "exists but connection failed previously" in caplog.text

    @pytest.mark.parametrize("stage", ["connect", "lookup", "create"])
    def test_fallback_errors_are_not_hidden(self, stage, mock_psycopg2, caplog):
        """Ошибки системного подключения, поиска и создания возвращаются вызывающему."""
        connect, cursor = mock_psycopg2
        connection = MagicMock()
        connection.__enter__.return_value = connection
        connection.cursor.return_value.__enter__.return_value = cursor
        failure = OperationalError("test fallback failure")
        connect.side_effect = [
            OperationalError("target unavailable"),
            failure if stage == "connect" else connection,
        ]
        cursor.fetchone.return_value = None
        if stage == "lookup":
            cursor.execute.side_effect = failure
        elif stage == "create":
            cursor.execute.side_effect = [None, failure]

        with pytest.raises(OperationalError) as caught:
            ensure_db_exists("host", "user", "test-only", "practice")

        assert caught.value is failure
        assert connect.call_count == 2
        assert "Failed to auto-create database" in caplog.text
        if stage == "connect":
            cursor.execute.assert_not_called()

    def test_unexpected_connection_error_does_not_trigger_creation(self, mock_psycopg2):
        """Ошибку программирования нельзя принимать за отсутствие целевой базы."""
        connect, _ = mock_psycopg2
        connect.side_effect = TypeError("invalid connection argument")

        with pytest.raises(TypeError, match="invalid connection argument"):
            ensure_db_exists("host", "user", "test-only", "practice")

        connect.assert_called_once()


class TestBootstrapFailureRegression:
    """Ошибки запуска должны останавливаться на соответствующей границе."""

    @pytest.mark.parametrize(
        "key",
        [
            "POSTGRES_HOST",
            "POSTGRES_DEFAULT_USER",
            "POSTGRES_DEFAULT_PASSWORD",
            "POSTGRES_DATABASE_NAME",
        ],
    )
    def test_incomplete_config_does_not_attempt_provisioning(
        self, key, mock_env_dev, monkeypatch, mocker, mock_db, mock_sqlalchemy_inspect
    ):
        """Неполная конфигурация не используется для создания другой базы."""
        monkeypatch.delenv("SQLALCHEMY_DATABASE_URI", raising=False)
        monkeypatch.setenv(key, "")
        provision = mocker.patch("database_bootstrap.ensure_db_exists")
        mock_sqlalchemy_inspect.has_table.return_value = False

        init_db(MagicMock())

        provision.assert_not_called()
        mock_db.create_all.assert_called_once()

    @pytest.mark.parametrize("stage", ["inspect", "has_table", "create_all"])
    def test_schema_failure_is_propagated_without_commit(
        self, stage, mock_env_dev, monkeypatch, mocker, mock_db, mock_sqlalchemy_inspect
    ):
        """Ошибка чтения или создания схемы не скрывается и не приводит к commit."""
        monkeypatch.setenv("SQLALCHEMY_DATABASE_URI", "sqlite:///:memory:")
        failure = RuntimeError("test schema failure")
        mock_sqlalchemy_inspect.has_table.return_value = False
        if stage == "inspect":
            mocker.patch("database_bootstrap.inspect", side_effect=failure)
        elif stage == "has_table":
            mock_sqlalchemy_inspect.has_table.side_effect = failure
        else:
            mock_db.create_all.side_effect = failure

        with pytest.raises(RuntimeError) as caught:
            init_db(MagicMock())

        assert caught.value is failure
        mock_db.session.commit.assert_not_called()
        if stage != "create_all":
            mock_db.create_all.assert_not_called()


@pytest.fixture
def bootstrap_database(tmp_path, monkeypatch):
    """Отдельная SQLite-БД с настоящими таблицами пользователей и журналов.

    Создаём только таблицы, нужные для этой проверки: весь набор моделей
    содержит особенности PostgreSQL, которые здесь не проверяются.
    """
    database_uri = f"sqlite:///{(tmp_path / 'bootstrap.sqlite').as_posix()}"
    monkeypatch.setenv("MODE", "dev")
    monkeypatch.setenv("SQLALCHEMY_DATABASE_URI", database_uri)
    application = Flask("bootstrap-regression")
    application.config["SQLALCHEMY_DATABASE_URI"] = database_uri
    db.init_app(application)
    with application.app_context():
        User.__table__.create(db.engine)
        SimulateLog.__table__.create(db.engine)
        try:
            yield application
        finally:
            db.session.remove()
            db.engine.dispose()


@pytest.mark.parametrize("states", [(False, True), (True, True), (False, False)])
def test_bootstrap_repairs_only_pending_rows_and_is_repeatable(
    bootstrap_database, states
):
    """Реальная БД: завершённые записи не меняются, повторный запуск безопасен."""
    previous_end = datetime(2020, 1, 1)
    for row_id, ready in enumerate(states, start=1):
        db.session.add(
            SimulateLog(
                id=row_id,
                author_id=42,
                network_guid=f"network-{row_id}",
                ready=ready,
                simulate_end=previous_end,
            )
        )
    db.session.commit()

    init_db(bootstrap_database)
    # Убираем кеш сессии, чтобы проверить сохранённые значения, а не объекты в памяти.
    db.session.remove()
    rows = db.session.query(SimulateLog).order_by(SimulateLog.id).all()
    assert len(rows) == len(states)
    first_result = [(row.id, row.ready, row.simulate_end) for row in rows]
    for row, was_ready in zip(rows, states, strict=True):
        assert row.ready is True
        if was_ready:
            assert row.simulate_end == previous_end
        else:
            assert row.simulate_end != previous_end

    init_db(bootstrap_database)
    db.session.remove()
    rows = db.session.query(SimulateLog).order_by(SimulateLog.id).all()
    assert [(row.id, row.ready, row.simulate_end) for row in rows] == first_result


def test_failed_pending_log_update_does_not_persist_partial_changes(
    bootstrap_database, caplog
):
    """Сбой посреди массового обновления не оставляет часть записей завершёнными.

    Триггер SQLite воспроизводит ошибку на второй строке настоящего UPDATE.
    Проверяем сохранённые данные после закрытия исходной сессии.
    """
    for row_id in (1, 2):
        db.session.add(
            SimulateLog(
                id=row_id, author_id=42, network_guid=f"network-{row_id}", ready=False
            )
        )
    db.session.commit()
    with db.engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TRIGGER fail_second_log BEFORE UPDATE ON simulate_log "
                "WHEN OLD.id = 2 BEGIN SELECT RAISE(ABORT, 'test update failure'); END"
            )
        )

    init_db(bootstrap_database)
    db.session.remove()

    rows = db.session.query(SimulateLog).order_by(SimulateLog.id).all()
    assert [row.ready for row in rows] == [False, False]
    assert [row.simulate_end for row in rows] == [None, None]
    assert "Error fixing nonemulated networks" in caplog.text
    # Вместо потенциально приватного текста драйвера проверяем безопасный контекст.
    assert "IntegrityError" in caplog.text
    assert "stage=repair_pending_logs" in caplog.text


def test_startup_interruption_is_not_swallowed(
    mock_env_dev, monkeypatch, mocker, mock_db, mock_sqlalchemy_inspect
):
    """Прерывание пользователем не превращается в успешное завершение запуска."""
    monkeypatch.setenv("SQLALCHEMY_DATABASE_URI", "sqlite:///:memory:")
    mock_sqlalchemy_inspect.has_table.return_value = True
    log_model = mocker.patch("database_bootstrap.SimulateLog")
    log_model.query.filter.return_value.update.side_effect = KeyboardInterrupt()

    with pytest.raises(KeyboardInterrupt):
        init_db(MagicMock())

    mock_db.session.commit.assert_not_called()
