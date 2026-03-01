import io
import sys
import types
from types import SimpleNamespace
import unittest.mock as um

from flask import Flask, session
import pytest


def _install_import_stubs():
    flask_login_mod = types.ModuleType("flask_login")

    class LoginManager:
        login_view = ""

        def user_loader(self, fn):
            return fn

        def unauthorized_handler(self, fn):
            return fn

        def init_app(self, app):
            return None

    def login_required(fn):
        def wrapped(*args, **kwargs):
            return fn(*args, **kwargs)

        wrapped.__wrapped__ = fn
        return wrapped

    flask_login_mod.LoginManager = LoginManager
    flask_login_mod.login_required = login_required
    flask_login_mod.current_user = SimpleNamespace(id=1, is_authenticated=True)
    flask_login_mod.login_user = lambda *args, **kwargs: None
    flask_login_mod.logout_user = lambda *args, **kwargs: None
    sys.modules["flask_login"] = flask_login_mod

    sqlalchemy_exc_mod = types.ModuleType("sqlalchemy.exc")

    class SQLAlchemyError(Exception):
        pass

    sqlalchemy_exc_mod.SQLAlchemyError = SQLAlchemyError
    sys.modules["sqlalchemy.exc"] = sqlalchemy_exc_mod

    miminet_config_mod = types.ModuleType("miminet_config")
    miminet_config_mod.make_example_net_switch_and_hub = lambda: "{}"
    sys.modules["miminet_config"] = miminet_config_mod

    miminet_model_mod = types.ModuleType("miminet_model")

    class User:
        query = SimpleNamespace(
            filter_by=lambda **kwargs: SimpleNamespace(first=lambda: None),
            filter=lambda *args, **kwargs: SimpleNamespace(first=lambda: None),
        )

        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

    class Network:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

    miminet_model_mod.User = User
    miminet_model_mod.Network = Network
    miminet_model_mod.db = SimpleNamespace(
        session=SimpleNamespace(
            add=lambda *args, **kwargs: None,
            commit=lambda *args, **kwargs: None,
            rollback=lambda *args, **kwargs: None,
        )
    )
    sys.modules["miminet_model"] = miminet_model_mod

    requests_mod = types.ModuleType("requests")
    requests_mod.get = lambda *args, **kwargs: SimpleNamespace(ok=True, content=b"")
    requests_mod.session = lambda: SimpleNamespace()
    sys.modules["requests"] = requests_mod

    oauthlib_oauth2 = types.ModuleType("oauthlib.oauth2")

    class TokenExpiredError(Exception):
        pass

    oauthlib_oauth2.TokenExpiredError = TokenExpiredError
    sys.modules["oauthlib.oauth2"] = oauthlib_oauth2

    requests_oauthlib = types.ModuleType("requests_oauthlib")

    class OAuth2Session:
        pass

    requests_oauthlib.OAuth2Session = OAuth2Session
    sys.modules["requests_oauthlib"] = requests_oauthlib

    id_token_mod = types.ModuleType("google.oauth2.id_token")
    id_token_mod.verify_oauth2_token = lambda **kwargs: {}

    google_oauth2 = types.ModuleType("google.oauth2")
    google_oauth2.id_token = id_token_mod

    google_transport_requests = types.ModuleType("google.auth.transport.requests")
    google_transport_requests.Request = object
    google_transport = types.ModuleType("google.auth.transport")
    google_transport.requests = google_transport_requests
    google_auth = types.ModuleType("google.auth")
    google_auth.transport = google_transport
    google_mod = types.ModuleType("google")
    google_mod.auth = google_auth
    google_mod.oauth2 = google_oauth2

    sys.modules["google"] = google_mod
    sys.modules["google.auth"] = google_auth
    sys.modules["google.auth.transport"] = google_transport
    sys.modules["google.auth.transport.requests"] = google_transport_requests
    sys.modules["google.oauth2"] = google_oauth2
    sys.modules["google.oauth2.id_token"] = id_token_mod

    flow_mod = types.ModuleType("google_auth_oauthlib.flow")

    class Flow:
        @classmethod
        def from_client_secrets_file(cls, *args, **kwargs):
            return SimpleNamespace(
                credentials=SimpleNamespace(_id_token="token"),
                redirect_uri="",
                authorization_url=lambda **kw: ("https://auth.local", "state"),
                fetch_token=lambda **kw: None,
            )

    flow_mod.Flow = Flow
    google_auth_oauthlib = types.ModuleType("google_auth_oauthlib")
    google_auth_oauthlib.flow = flow_mod
    sys.modules["google_auth_oauthlib"] = google_auth_oauthlib
    sys.modules["google_auth_oauthlib.flow"] = flow_mod

    cachecontrol_mod = types.ModuleType("pip._vendor.cachecontrol")
    cachecontrol_mod.CacheControl = lambda session: session
    sys.modules["pip._vendor.cachecontrol"] = cachecontrol_mod


_install_import_stubs()
import miminet_auth


@pytest.fixture
def mocker():
    patchers = []

    class _Mocker:
        Mock = um.Mock
        mock_open = um.mock_open
        ANY = um.ANY

        def patch(self, target, *args, **kwargs):
            patcher = um.patch(target, *args, **kwargs)
            patched = patcher.start()
            patchers.append(patcher)
            return patched

    tool = _Mocker()
    yield tool

    while patchers:
        patchers.pop().stop()


def _build_test_app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret"
    app.add_url_rule("/profile", endpoint="user_profile", view_func=lambda: "ok")
    app.add_url_rule("/login", endpoint="login_index", view_func=lambda: "login")
    app.add_url_rule("/home", endpoint="home", view_func=lambda: "home")
    app.add_url_rule(
        "/auth/google_callback", endpoint="google_callback", view_func=lambda: "google"
    )
    return app


def test_user_profile_get_splits_nick(mocker):
    app = _build_test_app()
    user = SimpleNamespace(id=1, nick="Ivan Petrov", avatar_uri="empty.jpg")
    query = mocker.Mock()
    query.filter_by.return_value.first.return_value = user

    mocker.patch("miminet_auth.current_user", SimpleNamespace(id=1))
    mocker.patch("miminet_auth.User.query", query)
    render_mock = mocker.patch("miminet_auth.render_template", return_value="rendered")

    with app.test_request_context("/profile", method="GET"):
        result = miminet_auth.user_profile.__wrapped__()

    assert result == "rendered"
    render_mock.assert_called_once_with(
        "auth/profile.html", user=user, first_name="Ivan", last_name="Petrov"
    )


def test_user_profile_post_rejects_invalid_avatar_extension(mocker):
    app = _build_test_app()
    user = SimpleNamespace(id=1, nick="Ivan Petrov", avatar_uri="empty.jpg")
    query = mocker.Mock()
    query.filter_by.return_value.first.return_value = user

    mocker.patch("miminet_auth.current_user", SimpleNamespace(id=1))
    mocker.patch("miminet_auth.User.query", query)
    flash_mock = mocker.patch("miminet_auth.flash")
    render_mock = mocker.patch("miminet_auth.render_template", return_value="rendered")
    commit_mock = mocker.patch("miminet_auth.db.session.commit")

    data = {
        "first_name": "Ivan",
        "last_name": "Petrov",
        "avatar": (io.BytesIO(b"bad"), "avatar.gif"),
    }
    with app.test_request_context(
        "/profile", method="POST", data=data, content_type="multipart/form-data"
    ):
        result = miminet_auth.user_profile.__wrapped__()

    assert result == "rendered"
    flash_mock.assert_called_once()
    commit_mock.assert_not_called()
    render_mock.assert_called_once()


def test_user_profile_post_updates_nick_and_redirects(mocker):
    app = _build_test_app()
    user = SimpleNamespace(id=1, nick="Old Name", avatar_uri="empty.jpg")
    query = mocker.Mock()
    query.filter_by.return_value.first.return_value = user

    mocker.patch("miminet_auth.current_user", SimpleNamespace(id=1))
    mocker.patch("miminet_auth.User.query", query)
    commit_mock = mocker.patch("miminet_auth.db.session.commit")

    with app.test_request_context(
        "/profile", method="POST", data={"first_name": "Alex", "last_name": "Lee"}
    ):
        response = miminet_auth.user_profile.__wrapped__()

    assert response.status_code == 302
    assert response.location.endswith("/profile")
    assert user.nick == "Alex Lee"
    commit_mock.assert_called_once()


def test_user_profile_post_saves_avatar_and_commits(mocker):
    app = _build_test_app()
    user = SimpleNamespace(id=1, nick="Old Name", avatar_uri="empty.jpg")
    query = mocker.Mock()
    query.filter_by.return_value.first.return_value = user

    mocker.patch("miminet_auth.current_user", SimpleNamespace(id=1))
    mocker.patch("miminet_auth.User.query", query)
    mocker.patch("miminet_auth.os.urandom", return_value=b"\x01" * 16)
    mocker.patch("werkzeug.datastructures.FileStorage.save")
    makedirs_mock = mocker.patch("miminet_auth.os.makedirs")
    commit_mock = mocker.patch("miminet_auth.db.session.commit")

    data = {
        "first_name": "",
        "last_name": "",
        "avatar": (io.BytesIO(b"img"), "my-avatar.JPG"),
    }
    with app.test_request_context(
        "/profile", method="POST", data=data, content_type="multipart/form-data"
    ):
        response = miminet_auth.user_profile.__wrapped__()

    assert response.status_code == 302
    assert response.location.endswith("/profile")
    assert user.avatar_uri == ("01" * 16) + ".jpg"
    makedirs_mock.assert_called_once_with("/app/static/avatar", exist_ok=True)
    commit_mock.assert_called_once()


def test_user_profile_post_without_updates_renders_page(mocker):
    app = _build_test_app()
    user = SimpleNamespace(id=1, nick="Single", avatar_uri="empty.jpg")
    query = mocker.Mock()
    query.filter_by.return_value.first.return_value = user

    mocker.patch("miminet_auth.current_user", SimpleNamespace(id=1))
    mocker.patch("miminet_auth.User.query", query)
    commit_mock = mocker.patch("miminet_auth.db.session.commit")
    render_mock = mocker.patch("miminet_auth.render_template", return_value="rendered")

    with app.test_request_context(
        "/profile", method="POST", data={"first_name": "", "last_name": ""}
    ):
        result = miminet_auth.user_profile.__wrapped__()

    assert result == "rendered"
    commit_mock.assert_not_called()
    render_mock.assert_called_once_with(
        "auth/profile.html", user=user, first_name="", last_name=""
    )


def test_google_callback_new_user_without_picture_uses_empty_avatar(mocker):
    app = _build_test_app()
    flow = mocker.Mock()
    flow.credentials = SimpleNamespace(_id_token="token")
    flow.fetch_token.return_value = None
    user_query = mocker.Mock()
    user_query.filter_by.return_value.first.side_effect = [None, SimpleNamespace(id=10)]
    user_ctor = mocker.patch("miminet_auth.User")

    mocker.patch("miminet_auth.Flow.from_client_secrets_file", return_value=flow)
    mocker.patch("miminet_auth.cachecontrol.CacheControl", return_value=mocker.Mock())
    mocker.patch("miminet_auth.google.auth.transport.requests.Request")
    mocker.patch("miminet_auth.User.query", user_query)
    mocker.patch(
        "miminet_auth.id_token.verify_oauth2_token",
        return_value={
            "sub": "g-1",
            "email": "u@test.local",
            "given_name": "A",
            "family_name": "B",
        },
    )
    mocker.patch("miminet_auth.Network")
    mocker.patch("miminet_auth.db.session.add")
    mocker.patch("miminet_auth.db.session.commit")
    mocker.patch("miminet_auth.requests.get")
    mocker.patch("miminet_auth.login_user")
    redirect_next_mock = mocker.patch(
        "miminet_auth.redirect_next_url", return_value="redirected"
    )

    with app.test_request_context("/auth/google_callback?state=state", method="GET"):
        session["state"] = "state"
        result = miminet_auth.google_callback()

    assert result == "redirected"
    assert user_ctor.call_args.kwargs["avatar_uri"] == "empty.jpg"
    redirect_next_mock.assert_called_once()
