import os
import json
import pytest
from pytest_mock import mocker
from flask import Flask, session, url_for
from miminet_auth import yandex_login, yandex_callback, login_index, db
from sqlalchemy.exc import SQLAlchemyError
from oauthlib.oauth2 import TokenExpiredError

@pytest.fixture
def app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = os.urandom(16).hex()
        
    with app.test_request_context():
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
        db.init_app(app)
        db.create_all()

        app.add_url_rule("/yandex_callback", methods=["GET"], view_func=yandex_callback)
        app.add_url_rule("/login_index", methods=["GET"], view_func=login_index)

        @app.route('/home')
        def home():
            pass

    return app

yandex_json = json.loads(os.environ.get("CLIENT_YANDEX"))

def test_yandex_login_initiates_request_to_yandex(app, mocker):
    """
    Test if yandex_login initiates a request to Yandex OAuth2 server
    """
    with app.test_request_context():
        mock_oauth2session = mocker.patch('miminet_auth.OAuth2Session')
        authorization_url = "https://example.com/auth"
        mocker.patch('miminet_auth.OAuth2Session.return_value.authorization_url',
                     return_value=(authorization_url, mocker))
        response = yandex_login(yandex_json)
        mock_oauth2session.return_value.authorization_url.assert_called_once_with(
            "https://oauth.yandex.ru/authorize", access_type="offline", prompt="consent"
        )
        assert response.status_code == 302
        assert response.location == authorization_url
        
def test_yandex_login_sets_correct_state_in_session(app, mocker):
    """
    Test if yandex_login sets the correct state in the session
    """
    with app.test_request_context():
        mocker.patch('miminet_auth.OAuth2Session')
        state = "test_state"
        mocker.patch('miminet_auth.OAuth2Session.return_value.authorization_url',
                     return_value=(mocker, state))
        yandex_login(yandex_json)
        assert session["state"] == state

def test_yandex_callback_requests_user_info_from_yandex(app, mocker):
    """
    Test if yandex_callback requests user info from Yandex API
    """
    with app.test_request_context():
        session['state']='test'
        mock_session_get = mocker.patch('miminet_auth.OAuth2Session')
        mocker.patch('miminet_auth.User')
        mocker.patch('miminet_auth.login_user')
        mock_fetch_token = mock_session_get.return_value
        mock_get = mock_session_get.return_value
        authorization_url = yandex_json["web"]["authorization_url"]
        token_uri = yandex_json["web"]["token_uri"]
        client_secret = yandex_json["web"]["client_secret"]
        yandex_callback(yandex_json)
        mock_fetch_token.fetch_token.assert_called_with(
                token_uri,
                authorization_response = authorization_url,
                client_secret = client_secret)
        mock_get.get.assert_called_with('https://login.yandex.ru/info')

def test_yandex_callback_handles_user_info_and_creates_user_in_db(app, mocker):
    """
    Test if yandex_callback handles user info and creates user in the database
    """
    with app.test_request_context():
        session['state']='test_state'
        mock_oauth2session = mocker.patch('miminet_auth.OAuth2Session')
        mock_user = mocker.patch('miminet_auth.User')
        mock_session = mocker.patch('miminet_auth.db.session')
        mocker.patch('miminet_auth.login_user')
        mock_get = mock_oauth2session.return_value.get
        mock_get.return_value.json.return_value = {
            "id": "test_id",
            "login": "test_login",
            "default_email": "test_email@example.com"
        }
        mock_user.query.filter_by().first.return_value = None
        yandex_callback(yandex_json)
        mock_user.assert_called_once_with(
            nick='test_login',
            yandex_id='test_id',
            email='test_email@example.com'
        )
        mock_session.add.assert_called_once_with(mock_user.return_value)
        mock_session.commit.assert_called_once()

def test_yandex_callback_redirects_to_home_after_login(app, mocker):
    """
    Test if yandex_callback redirects to home page after login
    """
    with app.test_request_context():
        session['state']='test_state'
        mock_user = mocker.patch('miminet_auth.User')
        mock_login_user = mocker.patch('miminet_auth.login_user')
        mocker.patch('miminet_auth.OAuth2Session')
        mock_user_filter = mock_user.query.filter_by().first
        response = yandex_callback(yandex_json)
        mock_login_user.assert_called_once_with(mock_user_filter.return_value, remember=True)
        assert response.status_code == 302
        assert response.location == url_for('home')

def test_yandex_callback_redirects_to_login_index_when_state_not_set(app, mocker):
    """
    Test if yandex_callback redirects to login index when state is not set
    """
    with app.test_request_context():
        session['state'] = None
        response = yandex_callback(yandex_json)
        assert response.status_code == 302
        assert response.location == url_for('login_index')

def test_yandex_callback_handles_user_not_added_to_db_error(app, mocker):
    """
    Test if yandex_callback handles error when user is not added to the database
    """
    with app.test_request_context():
        session['state'] = 'test_state'
        mock_user = mocker.patch('miminet_auth.User')
        mock_session = mocker.patch('miminet_auth.db.session')
        mock_flash = mocker.patch('miminet_auth.flash')
        mock_logger = mocker.patch('miminet_auth.logger.error')
        mock_user.query.filter_by().first.return_value = None
        mock_session.add.side_effect = SQLAlchemyError()
        with pytest.raises(Exception) as exc_info:
            response = yandex_callback(yandex_json)
            mock_logger.assert_called_with('Error while adding new Yandex user: %s', str(exc_info.value))
            mock_flash.assert_called_with(str(exc_info.value), category="error")
            assert response.status_code == 500
            assert response.location == url_for('login_index')

def test_yandex_callback_handles_token_expired_error(app, mocker):
    """
    Test if yandex_callback handles error when token is expired
    """
    with app.test_request_context():
        session['state'] = 'test_state'
        mock_oauth2session = mocker.patch('miminet_auth.OAuth2Session')
        mock_flash = mocker.patch('miminet_auth.flash')
        mock_logger = mocker.patch('miminet_auth.logger.error')
        mock_response = mock_oauth2session.return_value.get
        mock_response.return_value.json.return_value = {
            "id": "test_id",
            "login": "test_login",
            "default_email": "test_email@example.com"
        }
        mock_response.raise_for_status.side_effect = None
        mock_oauth2session.return_value.fetch_token.side_effect = TokenExpiredError()
        response = yandex_callback(yandex_json)
        mock_logger.assert_called_with('Token expired: %s', mocker.ANY)
        mock_flash.assert_called_with("Token expired. Please log in again.", category="error")
        assert response.status_code == 302
        assert response.location == url_for('login_index')