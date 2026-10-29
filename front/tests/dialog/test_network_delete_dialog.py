"""Проверяем настоящий диалог удаления с production CSRF в локальном браузере."""

from threading import Thread

import pytest
from playwright.sync_api import expect
from werkzeug.serving import make_server

from test_network_delete import deletion_app as deletion_app, deletion_state


@pytest.fixture
def deletion_page(deletion_app, page):
    """Поднимаем только диалог и реальный HTTP/ORM-путь без эмулятора и брокера."""
    server = make_server("127.0.0.1", 0, deletion_app.app, threaded=True)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{server.server_port}"
    page.context.add_cookies(
        [
            {
                "name": "access_token_cookie",
                "value": deletion_app.token,
                "url": origin,
                "httpOnly": True,
            },
            {"name": "csrf_access_token", "value": deletion_app.csrf, "url": origin},
        ]
    )

    def local_assets(route):
        # Оставляем реальные зависимости диалога, убираем аналитику и эмулятор.
        url = route.request.url
        scripts = (
            "/js/jquery-3.6.0.min.js",
            "/bootstrap.bundle.min.js",
            "/jwt_auth.js",
        )
        if not url.startswith(origin + "/"):
            route.abort()
        elif route.request.resource_type == "script" and not url.endswith(scripts):
            route.fulfill(status=200, body="", content_type="application/javascript")
        else:
            route.continue_()

    page.route("**/*", local_assets)
    try:
        page.goto(origin + "/web_network?guid=owner-network")
        page.locator("#net-settings").click()
        page.locator("#networkDeleteButton").click()
        expect(page.locator("#deleteNetConfirmModal")).to_be_visible()
        yield page, origin
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


@pytest.mark.parametrize("csrf_enabled", [True, False], ids=["prod", "dev"])
def test_confirm_deletes_network_with_cookie_csrf(
    deletion_page, deletion_app, csrf_enabled
):
    """Подтверждение передаёт CSRF и удаляет сеть вместо отказа авторизации."""
    page, origin = deletion_page
    deletion_app.app.config["JWT_COOKIE_CSRF_PROTECT"] = csrf_enabled
    if not csrf_enabled:
        page.context.clear_cookies(name="csrf_access_token")
    with page.expect_request(lambda r: "/delete_network?" in r.url) as deletion:
        page.locator("#networkDeleteSubmitButton").click()
    expect(page).to_have_url(origin + "/home")
    assert deletion.value.method == "POST"
    if csrf_enabled:
        assert deletion.value.headers["x-csrf-token"] == deletion_app.csrf
    else:
        assert "x-csrf-token" not in deletion.value.headers
    assert deletion_state() == ([20], [202])


def test_pending_delete_cannot_be_submitted_twice(deletion_page):
    """Ожидание ответа блокирует повторную отправку того же удаления."""
    page, _ = deletion_page
    pending = []
    page.route("**/delete_network?*", lambda route: pending.append(route))
    with page.expect_request(lambda r: "/delete_network?" in r.url):
        page.locator("#networkDeleteSubmitButton").click()
    expect(page.locator("#networkDeleteSubmitButton")).to_be_disabled()
    page.evaluate("document.getElementById('networkDeleteForm').requestSubmit()")
    assert len(pending) == 1
    assert deletion_state() == ([10, 20], [101, 202])
    pending[0].fulfill(status=500, body="error")
    expect(page.locator("#networkDeleteError")).to_be_visible()
    expect(page.locator("#networkDeleteSubmitButton")).to_be_enabled()


@pytest.mark.parametrize("cancel", ["#networkDeleteCancel", "#networkDeleteCancelIcon"])
def test_cancel_does_not_delete_network(deletion_page, cancel):
    """Оба способа отмены закрывают диалог без удаления данных."""
    page, origin = deletion_page
    page.locator(cancel).click()
    expect(page.locator("#deleteNetConfirmModal")).to_be_hidden()
    assert page.url == origin + "/web_network?guid=owner-network"
    assert deletion_state() == ([10, 20], [101, 202])


def test_server_failure_keeps_dialog_and_allows_retry(deletion_page):
    """При 500 показывается ошибка; повторная попытка доступна без ухода со страницы."""
    page, origin = deletion_page
    page.route(
        "**/delete_network?*", lambda route: route.fulfill(status=500, body="error")
    )
    page.locator("#networkDeleteSubmitButton").click()
    expect(page.locator("#networkDeleteError")).to_be_visible()
    expect(page.locator("#networkDeleteSubmitButton")).to_be_enabled()
    assert page.url == origin + "/web_network?guid=owner-network"
    assert deletion_state() == ([10, 20], [101, 202])
    page.unroute("**/delete_network?*")
    page.locator("#networkDeleteSubmitButton").click()
    expect(page).to_have_url(origin + "/home")
    assert deletion_state() == ([20], [202])
