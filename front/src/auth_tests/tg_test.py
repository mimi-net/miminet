import os
import json
import time
import hashlib
import hmac
import pytest
from flask import Flask, url_for
from miminet_auth import check_tg_authorization, tg_callback, login_index, db
from sqlalchemy.exc import SQLAlchemyError


@pytest.fixture
def app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = os.urandom(16).hex()

    with app.test_request_context():
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///test.db"
        db.init_app(app)
        db.create_all()

        app.add_url_rule("/tg_callback", methods=["GET"], view_func=tg_callback)
        app.add_url_rule("/login_index", methods=["GET"], view_func=login_index)

        @app.route("/home")
        def home():
            pass

    return app


@pytest.fixture
def auth_data():
    return {"id": "hash", "auth_date": str(int(time.time()))}


@pytest.fixture
def create_hash():
    bot_token_secret = os.environ.get("BOT_TOKEN")
    BOT_TOKEN = json.loads(bot_token_secret) if bot_token_secret else None
    auth_data = {"id": "hash", "auth_date": str(int(time.time()))}
    data_check_arr = [f"{key}={value}" for key, value in auth_data.items()]
    data_check_arr.sort()
    data_check_string = "\n".join(data_check_arr)
    secret_key = hashlib.sha256(BOT_TOKEN["token"]["BOT_TOKEN"].encode()).digest()
    hash_result = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()
    return hash_result, BOT_TOKEN


def test_check_tg_authorization_successful(app, mocker, auth_data, create_hash):
    """
    Test if check_tg_authorization successfully verifies valid Telegram authorization data
    """
    auth_data["hash"], BOT_TOKEN = create_hash
    mocker.patch("os.environ.get", return_value="BOT_TOKEN")
    with app.test_request_context():
        result = check_tg_authorization(auth_data, BOT_TOKEN)
    assert result == auth_data


def test_check_tg_authorization_invalid_data(app, auth_data):
    """
    Test if check_tg_authorization raises an exception for invalid Telegram authorization data
    """
    auth_data["hash"] = "invalid_hash"
    with pytest.raises(Exception):
        with app.test_request_context():
            check_tg_authorization(auth_data)


def test_check_tg_authorization_outdated_data(app, auth_data):
    """
    Test if check_tg_authorization raises an exception for outdated Telegram authorization data
    """
    auth_data["auth_date"] = str(int(time.time()) - 86401)
    with pytest.raises(Exception):
        with app.test_request_context():
            check_tg_authorization(auth_data)


def test_tg_callback_valid_user_data(app, mocker):
    """
    Test if tg_callback processes valid Telegram user data correctly
    """
    with app.test_request_context():
        test_user_json = (
            '{"id": test_id, "first_name": "test_name", "username": "test_username"}'
        )
        mock_json = mocker.patch("miminet_auth.json.loads")
        mocker.patch("miminet_auth.request.args.get", return_value=test_user_json)
        mocker.patch("miminet_auth.User")
        mocker.patch("miminet_auth.login_user")
        tg_callback()
        mock_json.assert_called_with(test_user_json)


def test_tg_callback_invalid_user_data(app, mocker):
    """
    Test if tg_callback handles invalid Telegram user data correctly
    """
    with app.test_request_context():
        flash_mock = mocker.patch("miminet_auth.flash")
        mocker.patch("miminet_auth.request.args.get", return_value=None)
        response = tg_callback()
        flash_mock.assert_called_with("Invalid Telegram user data", category="error")
        assert response.status_code == 302
        assert response.location == url_for("login_index")


def test_tg_callback_handles_user_info_and_creates_user_in_db(app, mocker):
    """
    Test if tg_callback handles user info and creates user in the database
    """
    with app.test_request_context():
        user_json = {
            "id": "test_id",
            "first_name": "test_name",
            "username": "test_username",
        }
        mock_user_data = mocker.patch("miminet_auth.json.loads")
        mock_user = mocker.patch("miminet_auth.User")
        mock_session = mocker.patch("miminet_auth.db.session")
        mocker.patch("miminet_auth.request.args.get")
        mocker.patch("miminet_auth.login_user")
        mocker.patch("miminet_auth.check_tg_authorization")
        mock_user_data.return_value = user_json
        mock_user.query.filter().first.return_value = None
        tg_callback()
        mock_user.assert_called_once_with(
            nick="test_name", tg_id="test_id", email="test_username"
        )
        mock_session.add.assert_called_once_with(mock_user.return_value)
        mock_session.commit.assert_called_once()


def test_tg_callback_redirects_to_home_after_login(app, mocker):
    """
    Test if tg_callback redirects to home page after login
    """
    with app.test_request_context():
        mock_login_user = mocker.patch("miminet_auth.login_user")
        mock_user = mocker.patch("miminet_auth.User")
        mocker.patch("miminet_auth.request.args.get")
        mocker.patch("miminet_auth.json.loads")
        mocker.patch("miminet_auth.check_tg_authorization")
        mock_user_filter = mock_user.query.filter().first
        response = tg_callback()
        mock_login_user.assert_called_once_with(
            mock_user_filter.return_value, remember=True
        )
        assert response.status_code == 302
        assert response.location == url_for("home")


def test_tg_callback_redirects_to_login_index_when_user_json_not_set(app, mocker):
    """
    Test if tg_callback redirects to login index when Telegram user JSON is not set
    """
    with app.test_request_context():
        mock_flash = mocker.patch("miminet_auth.flash")
        response = tg_callback()
        mock_flash.assert_called_with("Invalid Telegram user data", category="error")
        assert response.status_code == 302
        assert response.location == url_for("login_index")


def test_tg_callback_handles_user_not_added_to_db_error(app, mocker):
    """
    Test if tg_callback handles error when user is not added to the database
    """
    with app.test_request_context():
        mock_user = mocker.patch("miminet_auth.User")
        mock_session = mocker.patch("miminet_auth.db.session")
        mock_flash = mocker.patch("miminet_auth.flash")
        mock_logger = mocker.patch("miminet_auth.logger.error")
        mock_user.query.filter_by().first.return_value = None
        mock_session.add.side_effect = SQLAlchemyError()
        with pytest.raises(Exception) as exc_info:
            response = tg_callback()
            mock_logger.assert_called_with(
                "Error while adding new Yandex user: %s", str(exc_info.value)
            )
            mock_flash.assert_called_with(str(exc_info.value), category="error")
            assert response.status_code == 500
            assert response.location == url_for("login_index")


def test_tg_callback_handles_exception(app, mocker):
    """
    Test if tg_callback handles exceptions properly
    """
    with app.test_request_context():
        mock_check = mocker.patch("miminet_auth.check_tg_authorization")
        mock_flash = mocker.patch("miminet_auth.flash")
        mock_logger = mocker.patch("miminet_auth.logger.error")
        mock_check.add.side_effect = Exception()
        with pytest.raises(Exception):
            response = tg_callback()
            mock_logger.assert_called_with(
                "Error while processing Telegram callback: %s", "Test exception"
            )
            mock_flash.assert_called_with("Test exception", category="error")
            assert response.status_code == 500
            assert response.location == url_for("login_index")
