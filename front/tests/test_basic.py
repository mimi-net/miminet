import pytest
from requests import Session
from conftest.environment_setup import (
    MiminetTester,
    MAIN_PAGE,
    HOME_PAGE,
    selenium,
    requester,
    chrome_driver,
)


class TestAvailability:

    def test_auth(self, selenium: MiminetTester):
        """Checks if it possible to open home page (are we authorized or not)"""
        selenium.get(HOME_PAGE)

        assert selenium.title == "Веб-эмулятор"

    @pytest.mark.parametrize(
        "endpoint", ["/", "/auth/login.html", "/quiz/test/all", "/examples", "/home"]
    )
    def test_pages_availability(self, endpoint: str, requester: Session):
        """Checks accessibility for specified pages"""
        url = f"{MAIN_PAGE}{endpoint}"
        status_code = requester.get(url).status_code

        assert status_code == 200