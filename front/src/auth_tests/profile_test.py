import io
from datetime import timedelta
from types import SimpleNamespace

import miminet_auth
import pytest
from flask import Flask, session
from flask_jwt_extended import JWTManager
from werkzeug.exceptions import Forbidden


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
    app.add_url_rule(
        "/auth/google_callback", endpoint="google_callback", view_func=lambda: "google"
    )
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


def test_google_callback_new_user_without_picture_uses_empty_avatar(mocker):
    app = _build_test_app()
    flow = mocker.Mock()
    flow.credentials = SimpleNamespace(_id_token="token")
    flow.fetch_token.return_value = None
    filtered_query = mocker.Mock()
    filtered_query.first.side_effect = [None, SimpleNamespace(id=10)]
    user_query = mocker.Mock()
    user_query.filter_by.return_value = filtered_query
    user_ctor = mocker.patch("miminet_auth.User")
    user_ctor.query = user_query

    mocker.patch("miminet_auth.Flow.from_client_secrets_file", return_value=flow)
    mocker.patch("miminet_auth.cachecontrol.CacheControl", return_value=mocker.Mock())
    mocker.patch("miminet_auth.google.auth.transport.requests.Request")
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
    mocker.patch("miminet_auth.create_access_token")
    mocker.patch("miminet_auth.set_access_cookies", return_value="redirected")
    mocker.patch("miminet_auth.set_refresh_cookies", return_value="redirected")
    redirect_next_mock = mocker.patch(
        "miminet_auth.redirect_next_url", return_value="redirected"
    )

    with app.test_request_context("/auth/google_callback?state=state", method="GET"):
        session["state"] = "state"
        result = miminet_auth.google_callback()

    assert result == "redirected"
    assert user_ctor.call_args.kwargs["avatar_uri"] == "empty.jpg"
    redirect_next_mock.assert_called_once()


def test_login_index_allows_authenticated_telegram_link_mode(mocker):
    app = _build_test_app()
    current_user = SimpleNamespace(id=42, is_authenticated=True)

    mocker.patch("miminet_auth.current_user", current_user)
    render_mock = mocker.patch("miminet_auth.render_template", return_value="rendered")

    with app.test_request_context(
        "/login?next=user_profile&link_provider=tg", method="GET"
    ):
        result = miminet_auth.login_index()
        assert session["social_link_provider"] == "tg"
        assert session["social_link_user_id"] == 42
        assert session["social_link_redirect"] == "user_profile"

    assert result == "rendered"
    render_mock.assert_called_once_with("auth/login.html", user=current_user)


def test_google_callback_links_social_account_to_current_profile(mocker):
    app = _build_test_app()
    flow = mocker.Mock()
    flow.credentials = SimpleNamespace(_id_token="token")
    flow.fetch_token.return_value = None
    linked_user = SimpleNamespace(id=10, google_id=None)
    mocker.patch(
        "miminet_auth.current_user", SimpleNamespace(id=10, is_authenticated=True)
    )
    user_model = mocker.patch("miminet_auth.User")
    user_model.query.get.return_value = linked_user
    user_model.query.filter_by.return_value.first.return_value = None

    mocker.patch("miminet_auth.Flow.from_client_secrets_file", return_value=flow)
    mocker.patch("miminet_auth.cachecontrol.CacheControl", return_value=mocker.Mock())
    mocker.patch("miminet_auth.google.auth.transport.requests.Request")
    mocker.patch(
        "miminet_auth.id_token.verify_oauth2_token",
        return_value={"sub": "g-1", "email": "u@test.local"},
    )
    commit_mock = mocker.patch("miminet_auth.db.session.commit")
    login_user_mock = mocker.patch("miminet_auth.login_user")

    with app.test_request_context("/auth/google_callback?state=state", method="GET"):
        session["state"] = "state"
        session["social_link_provider"] = "google"
        session["social_link_user_id"] = 10
        session["social_link_redirect"] = "user_profile"
        response = miminet_auth.google_callback()
        assert "social_link_provider" not in session

    assert response.status_code == 302
    assert response.location.endswith("/profile")
    assert linked_user.google_id == "g-1"
    commit_mock.assert_called_once()
    login_user_mock.assert_not_called()


def test_google_callback_does_not_steal_existing_social_binding(mocker):
    app = _build_test_app()
    flow = mocker.Mock()
    flow.credentials = SimpleNamespace(_id_token="token")
    flow.fetch_token.return_value = None
    linked_user = SimpleNamespace(id=10, google_id=None)
    other_user = SimpleNamespace(id=11, google_id="g-1")
    mocker.patch(
        "miminet_auth.current_user", SimpleNamespace(id=10, is_authenticated=True)
    )
    user_model = mocker.patch("miminet_auth.User")
    user_model.query.get.return_value = linked_user
    user_model.query.filter_by.return_value.first.return_value = other_user

    mocker.patch("miminet_auth.Flow.from_client_secrets_file", return_value=flow)
    mocker.patch("miminet_auth.cachecontrol.CacheControl", return_value=mocker.Mock())
    mocker.patch("miminet_auth.google.auth.transport.requests.Request")
    mocker.patch(
        "miminet_auth.id_token.verify_oauth2_token",
        return_value={"sub": "g-1", "email": "u@test.local"},
    )
    flash_mock = mocker.patch("miminet_auth.flash")
    commit_mock = mocker.patch("miminet_auth.db.session.commit")
    login_user_mock = mocker.patch("miminet_auth.login_user")

    with app.test_request_context("/auth/google_callback?state=state", method="GET"):
        session["state"] = "state"
        session["social_link_provider"] = "google"
        session["social_link_user_id"] = 10
        session["social_link_redirect"] = "user_profile"
        response = miminet_auth.google_callback()

    assert response.status_code == 302
    assert response.location.endswith("/profile")
    assert linked_user.google_id is None
    commit_mock.assert_not_called()
    login_user_mock.assert_not_called()
    flash_mock.assert_called_once()


def test_tg_callback_links_social_account_to_current_profile(mocker):
    app = _build_test_app()
    linked_user = SimpleNamespace(id=5, tg_id=None)
    mocker.patch(
        "miminet_auth.current_user", SimpleNamespace(id=5, is_authenticated=True)
    )
    user_model = mocker.patch("miminet_auth.User")
    user_model.query.get.return_value = linked_user
    user_model.query.filter_by.return_value.first.return_value = None

    mocker.patch(
        "miminet_auth.json.loads",
        return_value={"id": 999, "first_name": "Test", "username": "tester"},
    )
    mocker.patch("miminet_auth.check_tg_authorization")
    commit_mock = mocker.patch("miminet_auth.db.session.commit")
    login_user_mock = mocker.patch("miminet_auth.login_user")

    with app.test_request_context("/auth/tg_callback?user=payload", method="GET"):
        session["social_link_provider"] = "tg"
        session["social_link_user_id"] = 5
        session["social_link_redirect"] = "user_profile"
        response = miminet_auth.tg_callback()

    assert response.status_code == 302
    assert response.location.endswith("/profile")
    assert linked_user.tg_id == "999"
    commit_mock.assert_called_once()
    login_user_mock.assert_not_called()
