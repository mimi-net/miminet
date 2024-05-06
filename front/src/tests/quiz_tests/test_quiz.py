import pytest

from app import app as flask_app
from app import db


# Config app
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


# Getting all quiz rules with GET method from flask_app
def get_method_cases():
    rules = flask_app.url_map.iter_rules()

    filtered_rules = [
        rule.rule
        for rule in rules
        if rule.rule.startswith("/quiz") and "GET" in rule.methods
    ]
    filtered_rules.append("/admin/")

    return filtered_rules


# Fixture to pass test cases --- routes
@pytest.fixture(params=get_method_cases())
def routes(request):
    return request.param


# Check unauthenticated user page access
def test_unauthenticated_pages_access(client, app, routes):
    app.config["LOGIN_DISABLED"] = False
    response = client.get(routes, follow_redirects=True)
    assert len(response.history) == 1
    assert response.request.path == "/auth/login.html"


# Check authenticated user quiz page access
def test_authenticated_page_access(client, app):
    with client:
        response = client.get("/quiz/test/all")
        assert response.status_code == 200
