"""
Тесты инициализации базы данных (функция init_db).

Проверяет что init_db() правильно вызывает ensure_db_exists()
с корректными параметрами для dev и prod режимов.
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock, call

# Добавляем путь к модулям приложения
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))


def test_init_db_dev_mode():
    """
    Тест инициализации БД в dev режиме.

    Проверяет что ensure_db_exists вызывается с параметрами локального PostgreSQL.
    """
    from miminet_model import init_db

    env_vars = {
        "MODE": "dev",
        "POSTGRES_HOST": "172.18.0.4",
        "POSTGRES_DEFAULT_USER": "postgres",
        "POSTGRES_DEFAULT_PASSWORD": "my_postgres",
        "POSTGRES_DATABASE_NAME": "miminet"
    }

    with patch.dict(os.environ, env_vars, clear=False):
        # Создаем минимальное Flask приложение
        from flask import Flask
        app = Flask(__name__)
        app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql+psycopg2://postgres:my_postgres@172.18.0.4/miminet"
        app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

        # Инициализируем db
        from miminet_model import db
        db.init_app(app)

        # Мокируем ensure_db_exists и операции БД
        with patch('miminet_model.ensure_db_exists') as mock_ensure, \
             patch.object(db.session, 'commit') as mock_commit, \
             patch('miminet_model.SimulateLog') as mock_simulate:

            # Настроить моки
            mock_ensure.return_value = True
            mock_simulate.query.filter.return_value.update.return_value = 0

            # Вызвать init_db
            init_db(app)

            # Проверить что ensure_db_exists вызвана с правильными параметрами
            mock_ensure.assert_called_once()
            args = mock_ensure.call_args[0]

            assert args[0] == "172.18.0.4"  # host
            assert args[1] == "postgres"    # user
            assert args[2] == "my_postgres" # password
            assert args[3] == "miminet"     # db name


def test_init_db_prod_mode():
    """
    Тест инициализации БД в prod режиме.

    Проверяет что ensure_db_exists вызывается с параметрами Yandex Cloud.
    """
    from miminet_model import init_db

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
        # Создаем минимальное Flask приложение
        from flask import Flask
        app = Flask(__name__)
        app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql+psycopg2://test_user:test_pass@test-cluster.mdb.yandexcloud.net:6432/miminet_prod?sslmode=require"
        app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

        # Инициализируем db
        from miminet_model import db
        db.init_app(app)

        # Мокируем ensure_db_exists и операции БД
        with patch('miminet_model.ensure_db_exists') as mock_ensure, \
             patch.object(db.session, 'commit') as mock_commit, \
             patch('miminet_model.SimulateLog') as mock_simulate:

            # Настроить моки
            mock_ensure.return_value = True
            mock_simulate.query.filter.return_value.update.return_value = 0

            # Вызвать init_db
            init_db(app)

            # Проверить что ensure_db_exists вызвана с Yandex параметрами
            mock_ensure.assert_called_once()
            args = mock_ensure.call_args[0]

            assert "mdb.yandexcloud.net" in args[0]  # host
            assert args[1] == "test_user"            # user
            assert args[2] == "test_pass"            # password
            assert args[3] == "miminet_prod"         # db name


def test_init_db_fixes_nonemulated_networks():
    """
    Тест что init_db исправляет незавершенные симуляции.

    Проверяет что SimulateLog записи с ready=False обновляются на ready=True.
    """
    from miminet_model import init_db

    env_vars = {
        "MODE": "dev",
        "POSTGRES_HOST": "172.18.0.4",
        "POSTGRES_DEFAULT_USER": "postgres",
        "POSTGRES_DEFAULT_PASSWORD": "my_postgres",
        "POSTGRES_DATABASE_NAME": "miminet"
    }

    with patch.dict(os.environ, env_vars, clear=False):
        from flask import Flask
        app = Flask(__name__)
        app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql+psycopg2://postgres:my_postgres@172.18.0.4/miminet"
        app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

        from miminet_model import db
        db.init_app(app)

        with patch('miminet_model.ensure_db_exists') as mock_ensure, \
             patch.object(db.session, 'commit') as mock_commit:

            mock_ensure.return_value = True

            # Мокируем SimulateLog.query
            mock_filter = MagicMock()
            mock_update = MagicMock()
            mock_filter.update.return_value = 3  # 3 записи обновлено

            with patch('miminet_model.SimulateLog') as mock_simulate_class:
                mock_simulate_class.query.filter.return_value = mock_filter

                # Вызвать init_db
                init_db(app)

                # Проверить что фильтр и update были вызваны
                mock_simulate_class.query.filter.assert_called()
                mock_filter.update.assert_called_with({"ready": True})


def test_init_db_creates_tables_if_not_exist():
    """
    Тест что init_db создает таблицы если БД пустая.

    Проверяет вызов db.create_all() при ошибке (БД не существует).
    """
    from miminet_model import init_db

    env_vars = {
        "MODE": "dev",
        "POSTGRES_HOST": "172.18.0.4",
        "POSTGRES_DEFAULT_USER": "postgres",
        "POSTGRES_DEFAULT_PASSWORD": "my_postgres",
        "POSTGRES_DATABASE_NAME": "miminet"
    }

    with patch.dict(os.environ, env_vars, clear=False):
        from flask import Flask
        app = Flask(__name__)
        app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql+psycopg2://postgres:my_postgres@172.18.0.4/miminet"
        app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

        from miminet_model import db
        db.init_app(app)

        with patch('miminet_model.ensure_db_exists') as mock_ensure, \
             patch.object(db, 'drop_all') as mock_drop, \
             patch.object(db, 'create_all') as mock_create, \
             patch.object(db.session, 'commit') as mock_commit:

            mock_ensure.return_value = False  # БД была создана (не существовала)

            # Симулируем ошибку при попытке обновить SimulateLog (БД пустая)
            with patch('miminet_model.SimulateLog') as mock_simulate:
                mock_simulate.query.filter.side_effect = Exception("Database not found")

                # Вызвать init_db
                init_db(app)

                # Проверить что были вызваны drop_all и create_all
                mock_drop.assert_called_once()
                mock_create.assert_called_once()


def test_init_db_unknown_mode_raises_error():
    """
    Тест что init_db выбрасывает ошибку при неизвестном MODE.
    """
    from miminet_model import init_db

    env_vars = {
        "MODE": "staging",  # Неизвестный режим
    }

    with patch.dict(os.environ, env_vars, clear=False):
        from flask import Flask
        app = Flask(__name__)

        # Устанавливаем фиктивный DATABASE_URI чтобы пройти инициализацию db
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

        from miminet_model import db
        db.init_app(app)

        # Ожидаем ValueError при вызове init_db с неизвестным MODE
        with pytest.raises(ValueError, match="Unknown MODE: staging"):
            init_db(app)


def test_init_db_with_missing_credentials():
    """
    Тест что init_db НЕ вызывает ensure_db_exists если отсутствуют credentials.
    """
    from miminet_model import init_db

    env_vars = {
        "MODE": "dev",
        # Не указываем POSTGRES_HOST и другие параметры
    }

    with patch.dict(os.environ, env_vars, clear=True):
        from flask import Flask
        app = Flask(__name__)
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

        from miminet_model import db
        db.init_app(app)

        with patch('miminet_model.ensure_db_exists') as mock_ensure, \
             patch.object(db.session, 'commit'):

            # Вызвать init_db
            try:
                init_db(app)
            except:
                pass  # Игнорируем ошибки

            # Проверить что ensure_db_exists НЕ был вызван
            mock_ensure.assert_not_called()
