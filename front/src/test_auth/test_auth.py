import os
import unittest
from unittest.mock import patch
import time
import hmac
import hashlib
from flask import Flask

from miminet_auth import yandex_login, check_tg_authorization

test_app = Flask(__name__)
test_app.config["TESTING"] = True
test_app.config["SECRET_KEY"] = os.urandom(16).hex()


class TestYandexLogin(unittest.TestCase):
    @patch("miminet_auth.OAuth2Session")
    @patch("miminet_auth.redirect")
    @patch("miminet_auth.url_for")
    def test_yandex_login(self, mock_url_for, mock_redirect, mock_oauth2session):
        session = {}

        mock_session_instance = mock_oauth2session.return_value
        mock_session_instance.authorization_url.return_value = (
            "mock_authorization_url",
            "mock_state",
        )

        mock_url_for.return_value = "mock_callback_url"

        session["state"] = "mock_state"

        with test_app.test_request_context():
            result = yandex_login()

        mock_session_instance.authorization_url.assert_called_once_with(
            "https://oauth.yandex.ru/authorize", access_type="offline", prompt="consent"
        )
        mock_url_for.assert_called_once_with("yandex_callback", _external=True)
        mock_redirect.assert_called_once_with("mock_authorization_url")
        self.assertEqual(session["state"], "mock_state")
        self.assertEqual(result, mock_redirect.return_value)


class TestCheckTGAuthorization(unittest.TestCase):
    def create_hash(self):
        BOT_TOKEN = os.environ["BOT_TOKEN"]
        auth_data = {"id": "hash", "auth_date": str(int(time.time()))}
        data_check_arr = [f"{key}={value}" for key, value in auth_data.items()]
        data_check_arr.sort()
        data_check_string = "\n".join(data_check_arr)
        secret_key = hashlib.sha256(BOT_TOKEN.encode()).digest()
        hash_result = hmac.new(
            secret_key, data_check_string.encode(), hashlib.sha256
        ).hexdigest()
        return hash_result

    def test_check_tg_authorization_successful(self):
        auth_data = {
            "hash": self.create_hash(),
            "auth_date": str(int(time.time())),
            "id": "hash",
        }

        with test_app.test_request_context():
            result = check_tg_authorization(auth_data)

        self.assertEqual(result, auth_data)

    def test_check_tg_authorization_invalid_data(self):
        auth_data = {"hash": "invalid_hash", "auth_date": str(int(time.time()))}

        with self.assertRaises(Exception):
            with test_app.test_request_context():
                check_tg_authorization(auth_data)

    def test_check_tg_authorization_outdated_data(self):
        auth_data = {"hash": "hash", "auth_date": str(int(time.time()) - 86401)}

        with self.assertRaises(Exception):
            with test_app.test_request_context():
                check_tg_authorization(auth_data)


if __name__ == "__main__":
    unittest.main()
