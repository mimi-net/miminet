"""Playwright fixtures mirroring the Selenium suite's ``conftest``.

The Selenium suite hand-rolls waiting helpers (``wait_and_click``,
``wait_until_appear``, ``wait_until_value``) because a WebDriver call fails
immediately when the element is missing or went stale. Playwright retries
locator actions until the element is actionable, so those helpers have no
counterpart here: ``page.click`` already carries the waiting and the stale-retry
loop. What remains are the helpers with real logic behind them -- the modal
context manager and the network-state readers -- which live in
``utils/networks.py`` next to this file.
"""

import os
from typing import Any, Generator, Optional

import pytest
import requests
from playwright._impl._api_structures import SetCookieParam
from playwright.sync_api import Browser, Page, Response, expect
from requests import Session


class testing_setting:
    """Configuration settings for testing environment."""

    target_host = os.getenv("TEST_TARGET_HOST", "172.18.0.2")
    port = int(os.getenv("TEST_TARGET_PORT", 80))
    viewport = {"width": 1920, "height": 1080}
    auth_data = {
        "email": "selenium",
        "password": "password",
    }  # this data should be inserted into the database


def _main_url() -> str:
    host = testing_setting.target_host
    port = testing_setting.port
    if port == 80:
        return f"http://{host}"
    return f"http://{host}:{port}"


MAIN_PAGE = _main_url()
HOME_PAGE = f"{MAIN_PAGE}/home"
LOGIN_PAGE = f"{MAIN_PAGE}//auth/login.html"

# Default timeout for expect() assertions, in milliseconds. Matches the 20s the
# Selenium helpers use.
DEFAULT_TIMEOUT = 20_000

# Navigations wait for the DOM, not for the `load` event. The home page lists
# every network the account owns and keeps `load` pending for ~30s once that
# list grows, which is long enough to exhaust the default timeout; the DOM
# itself is ready in well under a second. Selenium never hit this because
# `driver.get` returns on document readiness rather than on `load`.
WAIT_UNTIL = "domcontentloaded"

# Navigation gets its own, longer budget. The home page renders one preview per
# network the account owns, and every test run leaves more of them behind, so
# the DOM-ready point drifts upward as the account accumulates networks. The
# server itself is not the bottleneck -- it serves that page in ~10ms.
NAVIGATION_TIMEOUT = 60_000


@pytest.fixture(scope="session")
def requester() -> Generator[Session, None, None]:
    """Request session, used to send requests (GET, POST, etc...) and process their results"""
    session = requests.Session()

    response = session.get(MAIN_PAGE)
    assert response.status_code == 200, (
        "Miminet is not running or its address is incorrect: unable to get home page!"
    )

    response = session.post(
        f"{MAIN_PAGE}//auth/login.html",
        data=testing_setting.auth_data,
    )

    assert response.status_code == 200, "Unable to send authorization request!"
    assert response.url != LOGIN_PAGE, "Failed to login using the specified data"

    yield session

    session.close()


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict) -> dict:
    """Widen the viewport so the network panel matches the Selenium window size."""
    return {**browser_context_args, "viewport": testing_setting.viewport}


@pytest.fixture(scope="session")
def authorized_page(
    browser: Browser, requester: Session, browser_context_args: dict
) -> Generator[Page, None, None]:
    """Page that carries the ``requester`` session's cookies.

    Authorization is reused from the HTTP session rather than driven through the
    login form, which is what the Selenium suite does. Playwright takes the
    cookies as a context-level list, so unlike Selenium there is no need to open
    a page first to have a domain to attach them to.
    """
    context = browser.new_context(**browser_context_args)

    cookies: list[SetCookieParam] = [
        {
            "name": cookie.name,
            "value": cookie.value,
            "domain": testing_setting.target_host,
            "path": "/",
            "httpOnly": False,
            "secure": False,
            "sameSite": "Lax",
        }
        for cookie in requester.cookies
        if cookie.name and cookie.value
    ]
    context.add_cookies(cookies)

    page = context.new_page()
    page.set_default_timeout(DEFAULT_TIMEOUT)
    page.set_default_navigation_timeout(NAVIGATION_TIMEOUT)
    expect.set_options(timeout=DEFAULT_TIMEOUT)

    _goto = page.goto

    def goto(url: str, **kwargs: Any) -> Optional[Response]:
        kwargs.setdefault("wait_until", WAIT_UNTIL)
        return _goto(url, **kwargs)

    setattr(page, "goto", goto)

    yield page

    context.close()
