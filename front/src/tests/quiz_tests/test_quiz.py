import pytest

from app import app as flask_app
from app import db


@pytest.fixture()
def app():
    app = flask_app
    app.config["TESTING"] = True
    app.config["LOGIN_DISABLED"] = True
    app.config["WTF_CSRF_ENABLED"] = False

    with app.app_context():
        db.create_all()

    yield app


@pytest.fixture
def client(app):
    return app.test_client()


# Check unauthenticated user quiz page access
def test_unauthenticated_page_access(client, app):
    app.config["LOGIN_DISABLED"] = False
    response = client.get("/quiz/test/all", follow_redirects=True)
    assert len(response.history) == 1
    assert response.request.path == "/auth/login.html"


# Check authenticated user quiz page access
def test_authenticated_page_access(client, app):
    with client:
        response = client.get("/quiz/test/all")
        assert response.status_code == 200
