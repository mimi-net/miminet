"""
Интеграционные тесты подключения к базам данных.

- MODE=dev: реальное подключение к локальному PostgreSQL контейнеру
- MODE=prod: мокированное подключение (проверка параметров БЕЗ реального подключения к Yandex Cloud)
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from flask import Flask

# Добавляем путь к модулям приложения
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))


@pytest.fixture
def app_dev():
    """Фикстура Flask приложения для dev режима."""
    # Устанавливаем переменные окружения для dev
    env_vars = {
        "MODE": "dev",
        "POSTGRES_HOST": "172.18.0.4",
        "POSTGRES_DEFAULT_USER": "postgres",
        "POSTGRES_DEFAULT_PASSWORD": "my_postgres",
        "POSTGRES_DATABASE_NAME": "miminet"
    }

    with patch.dict(os.environ, env_vars, clear=False):
        # Импортируем приложение с установленными переменными
        from app import app

        app.config["TESTING"] = True

        yield app


def test_dev_database_connection(app_dev):
    """
    Тест реального подключения к локальному PostgreSQL в dev режиме.

    Требует запущенный postgres контейнер на 172.18.0.4.
    """
    from miminet_model import db

    with app_dev.app_context():
        # Попытка подключиться к БД
        try:
            connection = db.engine.connect()

            # Простой SQL запрос
            result = connection.execute(db.text("SELECT 1"))
            assert result.fetchone()[0] == 1

            # Проверить что это PostgreSQL
            result = connection.execute(db.text("SELECT version()"))
            version = result.fetchone()[0]
            assert "PostgreSQL" in version

            connection.close()
        except Exception as e:
            pytest.fail(f"Не удалось подключиться к dev БД: {e}")


def test_dev_database_uri_is_correct(app_dev):
    """Проверка что dev приложение использует правильный DATABASE_URI."""
    with app_dev.app_context():
        db_uri = app_dev.config["SQLALCHEMY_DATABASE_URI"]

        # Проверки
        assert "postgresql+psycopg2://" in db_uri
        assert "172.18.0.4" in db_uri
        assert "/miminet" in db_uri
        assert "sslmode" not in db_uri


def test_prod_database_connection_params():
    """
    Тест параметров подключения к Yandex Cloud (БЕЗ реального подключения).

    Используем моки для проверки корректности параметров.
    """
    env_vars = {
        "MODE": "prod",
        "YANDEX_POSTGRES_HOST": "test-cluster.mdb.yandexcloud.net",
        "YANDEX_POSTGRES_PORT": "6432",
        "YANDEX_POSTGRES_USER": "test_user",
        "YANDEX_POSTGRES_PASSWORD": "test_pass",
        "YANDEX_POSTGRES_DB": "miminet_prod",
        "YANDEX_POSTGRES_SSLMODE": "require"
    }

    with patch.dict(os.environ, env_vars, clear=False):
        from app import get_database_uri

        uri = get_database_uri("prod")

        # Проверить что URI содержит правильные параметры
        assert "postgresql+psycopg2://" in uri
        assert "test_user:test_pass" in uri
        assert "test-cluster.mdb.yandexcloud.net:6432" in uri
        assert "/miminet_prod" in uri
        assert "sslmode=require" in uri


def test_prod_ensure_db_exists_mock():
    """
    Тест вызова ensure_db_exists для prod с моком psycopg2.

    Проверяем что функция вызывает psycopg2.connect с правильными параметрами.
    """
    from miminet_model import ensure_db_exists

    # Мокируем psycopg2.connect
    with patch('miminet_model.psycopg2.connect') as mock_connect:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # Настроить моки
        mock_connect.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (1,)  # БД существует

        # Вызвать функцию
        result = ensure_db_exists(
            host="test-cluster.mdb.yandexcloud.net",
            user="test_user",
            password="test_pass",
            target_db="miminet_prod"
        )

        # Проверить что подключение было вызвано с правильными параметрами
        mock_connect.assert_called_once_with(
            dbname="postgres",
            user="test_user",
            password="test_pass",
            host="test-cluster.mdb.yandexcloud.net",
            port=5432  # ensure_db_exists использует 5432, а не 6432
        )

        # Проверить что был выполнен SELECT запрос для проверки существования БД
        assert mock_cursor.execute.called
        call_args = mock_cursor.execute.call_args_list[0][0][0]
        assert "SELECT 1 FROM pg_database WHERE datname" in call_args

        # Проверить результат
        assert result is True  # БД существует


def test_prod_ensure_db_exists_creates_database_mock():
    """
    Тест создания БД через ensure_db_exists для prod (с моком).

    Проверяем что если БД не существует, функция создает её.
    """
    from miminet_model import ensure_db_exists

    # Мокируем psycopg2.connect
    with patch('miminet_model.psycopg2.connect') as mock_connect:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # Настроить моки
        mock_connect.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None  # БД НЕ существует

        # Вызвать функцию
        result = ensure_db_exists(
            host="test-cluster.mdb.yandexcloud.net",
            user="test_user",
            password="test_pass",
            target_db="miminet_new"
        )

        # Проверить что был вызван CREATE DATABASE
        calls = [str(call) for call in mock_cursor.execute.call_args_list]
        assert any("CREATE DATABASE" in str(call) for call in calls)

        # Проверить результат
        assert result is False  # БД была создана (не существовала)


def test_dev_database_tables_exist(app_dev):
    """
    Тест что основные таблицы существуют в dev БД.

    Проверяет наличие таблиц: user, network, simulate, simulate_log.
    """
    from miminet_model import db

    with app_dev.app_context():
        try:
            connection = db.engine.connect()

            # Запрос списка таблиц
            result = connection.execute(db.text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public'"
            ))

            tables = [row[0] for row in result]

            # Проверить что основные таблицы существуют
            expected_tables = ["user", "network", "simulate", "simulate_log"]

            for table in expected_tables:
                assert table in tables, f"Таблица {table} не найдена в БД"

            connection.close()
        except Exception as e:
            pytest.fail(f"Не удалось проверить таблицы в dev БД: {e}")
