import pytest
from playwright.sync_api import Page, expect
from requests import Session

from conftest import HOME_PAGE, MAIN_PAGE


class TestAvailability:
    def test_auth(self, authorized_page: Page):
        """Checks if it possible to open home page (are we authorized or not)"""
        authorized_page.goto(HOME_PAGE)

        expect(authorized_page).to_have_title("Веб-эмулятор")

    @pytest.mark.parametrize(
        "endpoint",
        ["/", "/auth/login.html", "/quiz/test/all", "/examples", "/home", "/course"],
    )
    def test_pages_availability(self, endpoint: str, requester: Session):
        """Checks accessibility for specified pages"""
        url = f"{MAIN_PAGE}{endpoint}"
        status_code = requester.get(url).status_code

        assert status_code == 200
