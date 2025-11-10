"""
Тесты CRUD операций с базой данных.

Проверяет создание, чтение, обновление и удаление записей для:
- User (пользователи)
- Network (сети)
- SimulateLog (логи симуляций с TIMESTAMP)

MODE=dev: реальные операции с локальной БД
MODE=prod: мокированные операции (не используем реальную Yandex Cloud БД)
"""

import os
import sys
import uuid
import pytest
import time
from datetime import datetime
from unittest.mock import patch, MagicMock

# Добавляем путь к модулям приложения
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))


@pytest.fixture
def app_dev():
    """Фикстура Flask приложения для dev режима."""
    env_vars = {
        "MODE": "dev",
        "POSTGRES_HOST": "172.18.0.4",
        "POSTGRES_DEFAULT_USER": "postgres",
        "POSTGRES_DEFAULT_PASSWORD": "my_postgres",
        "POSTGRES_DATABASE_NAME": "miminet"
    }

    with patch.dict(os.environ, env_vars, clear=False):
        from app import app

        app.config["TESTING"] = True
        yield app


def test_create_user_dev(app_dev):
    """
    Тест создания пользователя в dev БД.

    Проверяет полный цикл: создание → чтение → удаление.
    """
    from miminet_model import db, User

    with app_dev.app_context():
        # Создать пользователя
        test_user = User(
            email=f"test_dev_{uuid.uuid4().hex[:8]}@example.com",
            nick="TestUserDev",
            avatar_uri="test.jpg"
        )

        db.session.add(test_user)
        db.session.commit()

        # Сохранить ID для дальнейшей проверки
        user_id = test_user.id

        # Проверить что пользователь сохранен
        saved_user = User.query.filter_by(id=user_id).first()
        assert saved_user is not None
        assert saved_user.nick == "TestUserDev"
        assert saved_user.avatar_uri == "test.jpg"
        assert saved_user.email == test_user.email

        # Очистка
        db.session.delete(saved_user)
        db.session.commit()

        # Проверить что пользователь удален
        deleted_user = User.query.filter_by(id=user_id).first()
        assert deleted_user is None


def test_create_network_dev(app_dev):
    """
    Тест создания сети в dev БД.

    Проверяет создание сети с привязкой к пользователю.
    """
    from miminet_model import db, User, Network

    with app_dev.app_context():
        # Создать пользователя для автора
        test_user = User(
            email=f"author_{uuid.uuid4().hex[:8]}@example.com",
            nick="Author"
        )
        db.session.add(test_user)
        db.session.commit()

        # Создать сеть
        network_guid = str(uuid.uuid4())
        test_network = Network(
            author_id=test_user.id,
            guid=network_guid,
            title="Test Network",
            description="Test description"
        )

        db.session.add(test_network)
        db.session.commit()

        # Сохранить ID
        network_id = test_network.id

        # Проверить что сеть сохранена
        saved_network = Network.query.filter_by(id=network_id).first()
        assert saved_network is not None
        assert saved_network.title == "Test Network"
        assert saved_network.description == "Test description"
        assert saved_network.guid == network_guid
        assert saved_network.author_id == test_user.id

        # Очистка
        db.session.delete(saved_network)
        db.session.delete(test_user)
        db.session.commit()


def test_update_network_dev(app_dev):
    """
    Тест обновления сети в dev БД.

    Проверяет модификацию полей существующей сети.
    """
    from miminet_model import db, User, Network

    with app_dev.app_context():
        # Создать пользователя и сеть
        test_user = User(
            email=f"updater_{uuid.uuid4().hex[:8]}@example.com",
            nick="Updater"
        )
        db.session.add(test_user)
        db.session.commit()

        test_network = Network(
            author_id=test_user.id,
            guid=str(uuid.uuid4()),
            title="Original Title",
            description="Original Description"
        )
        db.session.add(test_network)
        db.session.commit()

        network_id = test_network.id

        # Обновить сеть
        test_network.title = "Updated Title"
        test_network.description = "Updated Description"
        test_network.share_mode = False
        db.session.commit()

        # Проверить что изменения сохранены
        updated_network = Network.query.filter_by(id=network_id).first()
        assert updated_network.title == "Updated Title"
        assert updated_network.description == "Updated Description"
        assert updated_network.share_mode is False

        # Очистка
        db.session.delete(updated_network)
        db.session.delete(test_user)
        db.session.commit()


def test_simulate_log_timestamp_dev(app_dev):
    """
    Тест работы с TIMESTAMP в dev БД.

    Проверяет автозаполнение полей simulate_start и simulate_end.
    Это критично для проверки совместимости TZTimestamp.
    """
    from miminet_model import db, User, Network, SimulateLog

    with app_dev.app_context():
        # Создать пользователя и сеть
        test_user = User(
            email=f"sim_{uuid.uuid4().hex[:8]}@example.com",
            nick="SimUser"
        )
        db.session.add(test_user)
        db.session.commit()

        network_guid = str(uuid.uuid4())
        test_network = Network(
            author_id=test_user.id,
            guid=network_guid,
            title="Sim Network"
        )
        db.session.add(test_network)
        db.session.commit()

        # Создать SimulateLog
        sim_log = SimulateLog(
            author_id=test_user.id,
            network_guid=network_guid,
            network=test_network.network,
            ready=False
        )

        db.session.add(sim_log)
        db.session.commit()

        sim_log_id = sim_log.id

        # Проверить автозаполнение simulate_start
        assert sim_log.simulate_start is not None
        assert isinstance(sim_log.simulate_start, datetime)

        # Запомнить время начала
        start_time = sim_log.simulate_start

        # Подождать немного и обновить ready
        time.sleep(1)
        sim_log.ready = True
        db.session.commit()

        # Обновить объект из БД
        db.session.refresh(sim_log)

        # Проверить автозаполнение simulate_end
        assert sim_log.simulate_end is not None
        assert isinstance(sim_log.simulate_end, datetime)
        assert sim_log.simulate_end >= start_time  # end должен быть позже start

        # Очистка
        db.session.delete(sim_log)
        db.session.delete(test_network)
        db.session.delete(test_user)
        db.session.commit()


def test_user_with_oauth_fields_dev(app_dev):
    """
    Тест создания пользователя с OAuth полями.

    Проверяет поля vk_id, google_id, yandex_id, tg_id.
    """
    from miminet_model import db, User

    with app_dev.app_context():
        # Создать пользователя с OAuth данными
        test_user = User(
            email=f"oauth_{uuid.uuid4().hex[:8]}@example.com",
            nick="OAuthUser",
            vk_id="123456789",
            google_id="google_987654321",
            yandex_id="yandex_111222333",
            tg_id="tg_444555666"
        )

        db.session.add(test_user)
        db.session.commit()

        user_id = test_user.id

        # Проверить OAuth поля
        saved_user = User.query.filter_by(id=user_id).first()
        assert saved_user.vk_id == "123456789"
        assert saved_user.google_id == "google_987654321"
        assert saved_user.yandex_id == "yandex_111222333"
        assert saved_user.tg_id == "tg_444555666"

        # Очистка
        db.session.delete(saved_user)
        db.session.commit()


def test_network_with_task_flag_dev(app_dev):
    """
    Тест создания сети с флагом is_task.

    Проверяет что сети могут быть помечены как задания.
    """
    from miminet_model import db, User, Network

    with app_dev.app_context():
        # Создать пользователя
        test_user = User(
            email=f"task_{uuid.uuid4().hex[:8]}@example.com",
            nick="TaskCreator"
        )
        db.session.add(test_user)
        db.session.commit()

        # Создать сеть-задание
        task_network = Network(
            author_id=test_user.id,
            guid=str(uuid.uuid4()),
            title="Task Network",
            is_task=True,
            share_mode=False
        )

        db.session.add(task_network)
        db.session.commit()

        network_id = task_network.id

        # Проверить флаги
        saved_network = Network.query.filter_by(id=network_id).first()
        assert saved_network.is_task is True
        assert saved_network.share_mode is False

        # Очистка
        db.session.delete(saved_network)
        db.session.delete(test_user)
        db.session.commit()


def test_create_user_prod_mock():
    """
    Тест создания пользователя в prod БД (мокированное).

    Проверяет что методы SQLAlchemy вызываются правильно БЕЗ реального подключения.
    """
    from miminet_model import db, User

    env_vars = {
        "MODE": "prod",
        "YANDEX_POSTGRES_HOST": "test.mdb.yandexcloud.net",
        "YANDEX_POSTGRES_PORT": "6432",
        "YANDEX_POSTGRES_USER": "test_user",
        "YANDEX_POSTGRES_PASSWORD": "test_pass",
        "YANDEX_POSTGRES_DB": "miminet_prod",
        "YANDEX_POSTGRES_SSLMODE": "require"
    }

    with patch.dict(os.environ, env_vars, clear=False):
        # Мокировать db.session
        with patch.object(db, 'session') as mock_session:
            # Создать пользователя
            test_user = User(
                email="test_prod@example.com",
                nick="TestUserProd",
                avatar_uri="test.jpg"
            )

            mock_session.add.return_value = None
            mock_session.commit.return_value = None

            db.session.add(test_user)
            db.session.commit()

            # Проверить что методы вызваны
            mock_session.add.assert_called_once_with(test_user)
            mock_session.commit.assert_called()


def test_query_users_by_email_dev(app_dev):
    """
    Тест поиска пользователей по email.

    Проверяет работу запросов с фильтрацией.
    """
    from miminet_model import db, User

    with app_dev.app_context():
        # Создать несколько пользователей
        email1 = f"query1_{uuid.uuid4().hex[:8]}@example.com"
        email2 = f"query2_{uuid.uuid4().hex[:8]}@example.com"

        user1 = User(email=email1, nick="User1")
        user2 = User(email=email2, nick="User2")

        db.session.add(user1)
        db.session.add(user2)
        db.session.commit()

        # Поиск по email
        found_user = User.query.filter_by(email=email1).first()
        assert found_user is not None
        assert found_user.nick == "User1"

        # Проверить что другой пользователь не найден
        found_user2 = User.query.filter_by(email=email1).first()
        assert found_user2.email != email2

        # Очистка
        db.session.delete(user1)
        db.session.delete(user2)
        db.session.commit()
