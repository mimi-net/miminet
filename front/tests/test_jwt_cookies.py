"""Regression tests for prod JWT cookie handling (issue #550).

Background: f93fabd changed the prod JWT cookie scope from
``Domain=.BASE_DOMAIN`` to host-only (empty ``JWT_COOKIE_DOMAIN``). JWT
cookies are session cookies (no ``Expires``), so browsers kept sending the
stranded Domain-scoped copies; the server reads the stale (expired) copy
first and answers 401 "Token expired" forever — re-login does not help
because logout only clears the current scope. ``issue_jwt_cookies`` (used by
every login path and ``/refresh_access``) now explicitly expires the foreign
scope, and the browser sends ``X-CSRF-TOKEN`` (required in prod where
``JWT_COOKIE_CSRF_PROTECT=True``).
"""

import pytest

from app import app as flask_app
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_csrf_token,
)
from miminet_auth import clear_stale_scope_jwt_cookies, issue_jwt_cookies

_PROD_LIKE_CONFIG = {
    "JWT_SECRET_KEY": "test-secret-key-for-jwt-cookies-issue-550",
    "JWT_TOKEN_LOCATION": ["cookies", "headers"],
    "JWT_COOKIE_DOMAIN": None,  # host-only, current prod setup
    "JWT_COOKIE_SECURE": False,  # test client speaks plain http
    "JWT_COOKIE_CSRF_PROTECT": True,  # prod behavior under test
    "JWT_COOKIE_SAMESITE": "Lax",
}


@pytest.fixture
def prod_like_jwt(monkeypatch):
    """Run the real app with prod-like JWT settings (restored afterwards)."""
    monkeypatch.setenv("BASE_DOMAIN", "miminet.ru")
    snapshot = {key: flask_app.config.get(key) for key in _PROD_LIKE_CONFIG}
    flask_app.config.update(_PROD_LIKE_CONFIG)
    try:
        yield flask_app
    finally:
        flask_app.config.update(snapshot)


def _set_cookies(headers):
    return headers.getlist("Set-Cookie")


def test_login_issues_fresh_and_expires_legacy_domain_cookies(prod_like_jwt):
    """Fresh issuance must expire cookies stranded under the previous scope."""
    with prod_like_jwt.test_request_context("/"):
        access = create_access_token(identity="1")
        refresh = create_refresh_token(identity="1")
        response = prod_like_jwt.response_class(status=302)
        issue_jwt_cookies(response, access, refresh)
        headers = _set_cookies(response.headers)

    for name in ("access_token_cookie", "refresh_token_cookie"):
        # NOTE: Werkzeug strips the leading dot when dumping Set-Cookie, so
        # the legacy ".miminet.ru" scope appears as "Domain=miminet.ru" —
        # which still matches (and deletes) the old Domain-scoped cookies.
        legacy = [
            h
            for h in headers
            if h.startswith(f"{name}=") and "Domain=" in h and "miminet.ru" in h
        ]
        assert legacy, f"no legacy-scope deletion for {name}: {headers}"
        assert all("Max-Age=0" in h for h in legacy), legacy

        fresh = [
            h for h in headers if h.startswith(f"{name}=") and "Max-Age=0" not in h
        ]
        assert fresh, f"no fresh cookie for {name}: {headers}"
        assert all("Domain=" not in h for h in fresh), fresh


def test_login_expires_host_only_when_domain_scoped(prod_like_jwt, monkeypatch):
    """Reverse migration must also be covered (domain scope is current)."""
    prod_like_jwt.config["JWT_COOKIE_DOMAIN"] = ".miminet.ru"
    with prod_like_jwt.test_request_context("/"):
        response = prod_like_jwt.response_class(status=302)
        clear_stale_scope_jwt_cookies(response)
        headers = _set_cookies(response.headers)

    host_only = [
        h
        for h in headers
        if h.startswith("access_token_cookie=")
        and "Max-Age=0" in h
        and "Domain=" not in h
    ]
    assert host_only, f"no host-only deletion issued: {headers}"


def test_refresh_access_requires_csrf_token(prod_like_jwt):
    """POST /refresh_access without X-CSRF-TOKEN must be rejected in prod."""
    with prod_like_jwt.app_context():
        refresh = create_refresh_token(identity="1")
        csrf = get_csrf_token(refresh)

    client = prod_like_jwt.test_client()
    client.set_cookie("refresh_token_cookie", refresh)
    client.set_cookie("csrf_refresh_token", csrf)

    # The browser always sends X-Requested-With via ajaxWithAuth; without it
    # the backend answers non-API failures with a login redirect (302).
    response = client.post(
        "/refresh_access", headers={"X-Requested-With": "XMLHttpRequest"}
    )
    assert response.status_code == 401


def test_refresh_access_with_csrf_clears_stale_scope(prod_like_jwt):
    """Valid refresh must succeed and carry stale-scope deletions."""
    with prod_like_jwt.app_context():
        refresh = create_refresh_token(identity="1")
        csrf = get_csrf_token(refresh)

    client = prod_like_jwt.test_client()
    client.set_cookie("refresh_token_cookie", refresh)
    client.set_cookie("csrf_refresh_token", csrf)

    response = client.post(
        "/refresh_access",
        headers={
            "X-Requested-With": "XMLHttpRequest",
            "X-CSRF-TOKEN": csrf,
        },
    )
    assert response.status_code == 200

    headers = _set_cookies(response.headers)
    legacy = [
        h
        for h in headers
        if "access_token_cookie=" in h
        and "Domain=" in h
        and "miminet.ru" in h
        and "Max-Age=0" in h
    ]
    assert legacy, f"refresh did not clear legacy scope: {headers}"
