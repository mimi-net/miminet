"""Регрессии удаления сети с cookie JWT и включённой CSRF-защитой (#552)."""

from pathlib import Path
from types import SimpleNamespace

import pytest
from flask import Flask, redirect, render_template, request, send_from_directory
from flask_jwt_extended import JWTManager, create_access_token, get_csrf_token
from sqlalchemy import event

from app import app as configured_app, missing_token_callback
from miminet_model import Network, Simulate, User, db
from miminet_network import delete_network


@pytest.fixture
def deletion_app(tmp_path):
    """Изолируем реальные обработчик, шаблон и JWT от внешних сервисов."""
    source = Path(__file__).resolve().parents[1] / "src"
    application = Flask(
        "network-delete-regression",
        template_folder=str(source / "templates"),
        static_folder=str(source / "static"),
    )
    application.config.update(
        TESTING=True,
        SECRET_KEY="network-delete-session-test-only",
        JWT_SECRET_KEY="network-delete-jwt-test-key-at-least-32-characters",
        JWT_TOKEN_LOCATION=["cookies"],
        JWT_COOKIE_CSRF_PROTECT=True,
        JWT_COOKIE_SECURE=False,
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{(tmp_path / 'delete.sqlite').as_posix()}",
    )
    jwt = JWTManager(application)
    jwt.unauthorized_loader(missing_token_callback)
    db.init_app(application)

    # Остальные адреса нужны настоящему базовому шаблону для url_for.
    def unused(**kwargs):
        return "unused"

    for rule in configured_app.url_map.iter_rules():
        if rule.endpoint == "static":
            continue
        application.add_url_rule(
            rule.rule,
            endpoint=rule.endpoint,
            view_func=unused,
            methods=sorted((rule.methods or set()) - {"HEAD", "OPTIONS"}),
        )
    application.view_functions["delete_network"] = delete_network
    application.view_functions["home"] = lambda: "Мои сети"
    application.view_functions["login_index"] = lambda: ("Нужна авторизация", 401)

    def editor():
        network = Network.query.filter_by(guid=request.args.get("guid")).first()
        if network is None:
            return redirect("/home")
        user = SimpleNamespace(is_authenticated=True, config=None, avatar_uri=None)
        return render_template("base.html", network=network, current_user=user)

    application.view_functions["web_network"] = editor
    application.add_url_rule(
        "/assets/<path:filename>",
        view_func=lambda filename: send_from_directory(
            source / "static/assets", filename
        ),
    )

    with application.app_context():

        @event.listens_for(db.engine, "connect")
        def enable_foreign_keys(connection, _record):
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        tables = [User.__table__, Network.__table__, Simulate.__table__]
        db.metadata.create_all(db.engine, tables=tables)
        db.session.add_all([User(id=1, nick="Владелец"), User(id=2, nick="Другой")])
        db.session.flush()
        db.session.add_all(
            [
                Network(id=10, author_id=1, guid="owner-network"),
                Network(id=20, author_id=2, guid="other-network"),
            ]
        )
        db.session.flush()
        db.session.add_all(
            [
                Simulate(id=101, network_id=10, ready=True, packets="owner-packets"),
                Simulate(id=202, network_id=20, ready=True, packets="other-packets"),
            ]
        )
        db.session.commit()
        token = create_access_token(identity="1")
        csrf = get_csrf_token(token)
        try:
            yield SimpleNamespace(app=application, token=token, csrf=csrf)
        finally:
            db.session.remove()
            db.engine.dispose()


def deletion_state():
    """Перечитываем сохранённые сети и результаты после HTTP-запроса."""
    db.session.remove()
    return (
        [network.id for network in Network.query.order_by(Network.id)],
        [result.id for result in Simulate.query.order_by(Simulate.id)],
    )


@pytest.mark.parametrize("csrf", [None, "wrong-token"])
def test_delete_rejects_missing_or_wrong_csrf(deletion_app, csrf):
    """Cookie JWT не разрешает удаление без соответствующего CSRF-токена."""
    client = deletion_app.app.test_client()
    client.set_cookie("access_token_cookie", deletion_app.token)
    headers = {"X-Requested-With": "XMLHttpRequest"}
    if csrf is not None:
        headers["X-CSRF-TOKEN"] = csrf
    response = client.post("/delete_network?guid=owner-network", headers=headers)
    assert response.status_code == 401
    assert deletion_state() == ([10, 20], [101, 202])


@pytest.mark.parametrize("guid", ["owner-network", "other-network", "missing", ""])
def test_authenticated_delete_preserves_other_networks(deletion_app, guid):
    """С корректным CSRF удаляются только своя сеть и её результаты."""
    client = deletion_app.app.test_client()
    client.set_cookie("access_token_cookie", deletion_app.token)
    response = client.post(
        "/delete_network",
        query_string={"guid": guid},
        headers={"X-CSRF-TOKEN": deletion_app.csrf},
    )
    assert response.status_code == 302
    expected = ([20], [202]) if guid == "owner-network" else ([10, 20], [101, 202])
    assert deletion_state() == expected


def test_get_does_not_delete_network(deletion_app):
    """Открытие адреса удаления обычным GET сохраняет данные."""
    client = deletion_app.app.test_client()
    client.set_cookie("access_token_cookie", deletion_app.token)
    assert client.get("/delete_network?guid=owner-network").status_code == 302
    assert deletion_state() == ([10, 20], [101, 202])


def test_anonymous_delete_preserves_network(deletion_app):
    """CSRF-заголовок без JWT не даёт удалить сеть."""
    response = deletion_app.app.test_client().post(
        "/delete_network?guid=owner-network",
        headers={
            "X-Requested-With": "XMLHttpRequest",
            "X-CSRF-TOKEN": deletion_app.csrf,
        },
    )
    assert response.status_code == 401
    assert deletion_state() == ([10, 20], [101, 202])
