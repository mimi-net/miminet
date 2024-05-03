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


def get_method_cases(app):
    rules = app.url_map.iter_rules()

    filtered_rules = [rule.rule for rule in rules if rule.rule.startswith("/quiz") and 'GET' in rule.methods]
    filtered_rules.append("/admin/")

    return filtered_rules


def test_unauthenticated_pages_access(client, app):
    quiz_routes = get_method_cases(app)
    app.config["LOGIN_DISABLED"] = False
    for route in quiz_routes:
        response = client.get(route, follow_redirects=True)
        assert len(response.history) == 1
        assert response.request.path == "/auth/login.html"


# Check authenticated user quiz page access
def test_authenticated_page_access(client, app):
    with client:
        response = client.get("/quiz/test/all")
        assert response.status_code == 200
