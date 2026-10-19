import io
from datetime import timedelta
from types import SimpleNamespace

import pytest
from flask import Flask
from werkzeug.exceptions import Forbidden

import miminet_auth
from flask_jwt_extended import JWTManager


def _build_test_app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret"
    app.config.update(
        JWT_SECRET_KEY="test-secret",
        JWT_TOKEN_LOCATION=["cookies"],
        JWT_COOKIE_DOMAIN=".localhost",
        JWT_COOKIE_SECURE=False,  # True,
        JWT_COOKIE_CSRF_PROTECT=False,
        JWT_COOKIE_SAMESITE="Lax",
        JWT_ACCESS_TOKEN_EXPIRES=timedelta(hours=1),
        JWT_REFRESH_TOKEN_EXPIRES=timedelta(hours=2),
    )
    app.add_url_rule("/profile", endpoint="user_profile", view_func=lambda: "ok")
    app.add_url_rule("/login", endpoint="login_index", view_func=lambda: "login")
    app.add_url_rule("/home", endpoint="home", view_func=lambda: "home")
    JWTManager(app)
    return app


def test_user_profile_get_splits_nick(mocker):
    app = _build_test_app()
    user = SimpleNamespace(id=1, nick="Ivan Petrov", avatar_uri="empty.jpg")

    mocker.patch("miminet_auth.current_user", SimpleNamespace(id=1))
    user_model = mocker.patch("miminet_auth.User")
    user_model.query.filter_by.return_value.first.return_value = user
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

    mocker.patch("miminet_auth.current_user", SimpleNamespace(id=1))
    user_model = mocker.patch("miminet_auth.User")
    user_model.query.filter_by.return_value.first.return_value = user
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

    mocker.patch("miminet_auth.current_user", SimpleNamespace(id=1))
    user_model = mocker.patch("miminet_auth.User")
    user_model.query.filter_by.return_value.first.return_value = user
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

    mocker.patch("miminet_auth.current_user", SimpleNamespace(id=1))
    user_model = mocker.patch("miminet_auth.User")
    user_model.query.filter_by.return_value.first.return_value = user
    mocker.patch("miminet_auth.os.urandom", return_value=b"\x01" * 16)
    mocker.patch("builtins.open", mocker.mock_open())
    makedirs_mock = mocker.patch("miminet_auth.os.makedirs")
    commit_mock = mocker.patch("miminet_auth.db.session.commit")

    data = {
        "avatar": (io.BytesIO(b"img"), "my-avatar.JPG"),
    }
    with app.test_request_context(
        "/profile", method="POST", data=data, content_type="multipart/form-data"
    ):
        response = miminet_auth.user_profile.__wrapped__()

    assert response.status_code == 302
    assert response.location.endswith("/profile")
    assert user.avatar_uri == f"0/1/{('01' * 16)}.jpg"
    makedirs_mock.assert_called_once_with("/app/static/avatar/0/1", exist_ok=True)
    commit_mock.assert_called_once()


def test_user_profile_post_without_updates_renders_page(mocker):
    app = _build_test_app()
    user = SimpleNamespace(id=1, nick="Single", avatar_uri="empty.jpg")

    mocker.patch("miminet_auth.current_user", SimpleNamespace(id=1))
    user_model = mocker.patch("miminet_auth.User")
    user_model.query.filter_by.return_value.first.return_value = user
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


def test_user_profile_view_forbidden_without_permission(mocker):
    app = _build_test_app()

    mocker.patch("miminet_auth.current_user", SimpleNamespace(id=1, role=0))

    with app.test_request_context("/profile/2", method="GET"):
        with pytest.raises(Forbidden):
            miminet_auth.user_profile_view.__wrapped__(2)
