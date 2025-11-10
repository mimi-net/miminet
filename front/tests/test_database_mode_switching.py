"""
Unit-тесты для функции переключения режимов работы с БД (MODE=dev/prod).

Проверяет корректность генерации DATABASE_URI для разных режимов:
- MODE=dev -> локальный PostgreSQL контейнер
- MODE=prod -> Yandex Cloud PostgreSQL кластер
"""

import os
import sys
import pytest
from unittest.mock import patch

# Добавляем путь к модулям приложения
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))


def test_get_database_uri_dev_mode():
    """Тест генерации URI для dev режима (локальный PostgreSQL)."""
    env_vars = {
        "POSTGRES_HOST": "172.18.0.4",
        "POSTGRES_DEFAULT_USER": "postgres",
        "POSTGRES_DEFAULT_PASSWORD": "my_postgres",
        "POSTGRES_DATABASE_NAME": "miminet"
    }

    with patch.dict(os.environ, env_vars, clear=False):
        # Импортируем здесь, чтобы переменные окружения были установлены
        from app import get_database_uri

        uri = get_database_uri("dev")

        # Проверки
        assert "postgresql+psycopg2://" in uri
        assert "postgres:my_postgres" in uri
        assert "172.18.0.4" in uri
        assert "/miminet" in uri
        assert "sslmode" not in uri  # dev не использует SSL

        # Проверить что это действительно dev URI
        expected = "postgresql+psycopg2://postgres:my_postgres@172.18.0.4/miminet"
        assert uri == expected


def test_get_database_uri_prod_mode():
    """Тест генерации URI для prod режима (Yandex Cloud PostgreSQL)."""
    env_vars = {
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

        # Проверки
        assert "postgresql+psycopg2://" in uri
        assert "test_user:test_pass" in uri
        assert "test-cluster.mdb.yandexcloud.net:6432" in uri
        assert "/miminet_prod" in uri
        assert "sslmode=require" in uri  # prod использует SSL

        # Проверить полный URI
        expected = "postgresql+psycopg2://test_user:test_pass@test-cluster.mdb.yandexcloud.net:6432/miminet_prod?sslmode=require"
        assert uri == expected


def test_get_database_uri_prod_missing_credentials():
    """Тест что prod режим требует обязательные credentials."""
    # Тестируем несколько сценариев отсутствия credentials

    # Сценарий 1: пустой host
    env_vars_empty_host = {
        "YANDEX_POSTGRES_HOST": "",
        "YANDEX_POSTGRES_USER": "user",
        "YANDEX_POSTGRES_PASSWORD": "pass"
    }

    with patch.dict(os.environ, env_vars_empty_host, clear=True):
        from app import get_database_uri

        with pytest.raises(ValueError, match="Missing Yandex Cloud PostgreSQL credentials"):
            get_database_uri("prod")

    # Сценарий 2: отсутствует user
    env_vars_no_user = {
        "YANDEX_POSTGRES_HOST": "test.mdb.yandexcloud.net",
        "YANDEX_POSTGRES_USER": "",
        "YANDEX_POSTGRES_PASSWORD": "pass"
    }

    with patch.dict(os.environ, env_vars_no_user, clear=True):
        from app import get_database_uri

        with pytest.raises(ValueError, match="Missing Yandex Cloud PostgreSQL credentials"):
            get_database_uri("prod")

    # Сценарий 3: отсутствует password
    env_vars_no_password = {
        "YANDEX_POSTGRES_HOST": "test.mdb.yandexcloud.net",
        "YANDEX_POSTGRES_USER": "user",
        "YANDEX_POSTGRES_PASSWORD": ""
    }

    with patch.dict(os.environ, env_vars_no_password, clear=True):
        from app import get_database_uri

        with pytest.raises(ValueError, match="Missing Yandex Cloud PostgreSQL credentials"):
            get_database_uri("prod")


def test_get_database_uri_unknown_mode():
    """Тест что неизвестный MODE вызывает ошибку."""
    from app import get_database_uri

    # Тестируем различные неизвестные режимы
    invalid_modes = ["staging", "test", "local", "production", "PROD", "DEV"]

    for mode in invalid_modes:
        with pytest.raises(ValueError, match=f"Unknown MODE: {mode}"):
            get_database_uri(mode)


def test_get_database_uri_prod_default_port():
    """Тест что порт по умолчанию 6432 используется для prod если не указан."""
    env_vars = {
        "YANDEX_POSTGRES_HOST": "test-cluster.mdb.yandexcloud.net",
        # YANDEX_POSTGRES_PORT не указан
        "YANDEX_POSTGRES_USER": "test_user",
        "YANDEX_POSTGRES_PASSWORD": "test_pass",
        "YANDEX_POSTGRES_DB": "miminet_prod",
        "YANDEX_POSTGRES_SSLMODE": "require"
    }

    with patch.dict(os.environ, env_vars, clear=True):
        from app import get_database_uri

        uri = get_database_uri("prod")

        # Проверить что используется порт 6432 по умолчанию
        assert ":6432/" in uri


def test_get_database_uri_prod_default_sslmode():
    """Тест что sslmode по умолчанию 'require' используется для prod если не указан."""
    env_vars = {
        "YANDEX_POSTGRES_HOST": "test-cluster.mdb.yandexcloud.net",
        "YANDEX_POSTGRES_PORT": "6432",
        "YANDEX_POSTGRES_USER": "test_user",
        "YANDEX_POSTGRES_PASSWORD": "test_pass",
        "YANDEX_POSTGRES_DB": "miminet_prod",
        # YANDEX_POSTGRES_SSLMODE не указан
    }

    with patch.dict(os.environ, env_vars, clear=True):
        from app import get_database_uri

        uri = get_database_uri("prod")

        # Проверить что используется sslmode=require по умолчанию
        assert "sslmode=require" in uri
