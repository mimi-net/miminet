import io
from types import SimpleNamespace

import pytest
from flask import Flask, session
from werkzeug.exceptions import Forbidden

import miminet_auth


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
    user_query = mocker.Mock()
    user_query.filter_by.return_value.first.side_effect = [None, SimpleNamespace(id=10)]
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
    redirect_next_mock = mocker.patch(
        "miminet_auth.redirect_next_url", return_value="redirected"
    )

    with app.test_request_context("/auth/google_callback?state=state", method="GET"):
        session["state"] = "state"
        result = miminet_auth.google_callback()

    assert result == "redirected"
    assert user_ctor.call_args.kwargs["avatar_uri"] == "empty.jpg"
    redirect_next_mock.assert_called_once()
