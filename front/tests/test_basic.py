import pytest
from requests import Session
from conftest import (
    MiminetTester,
    MAIN_PAGE,
    HOME_PAGE,
)


class TestAvailability:

    def test_auth(self, selenium: MiminetTester):
        """Checks if it possible to open home page (are we authorized or not)"""
        selenium.get(HOME_PAGE)

        # Проверяем, что заголовок существует (не зависит от языка)
        # "Веб-эмулятор" на русском или "Web-Emulator" на английском
        assert selenium.title in ["Веб-эмулятор", "Web-Emulator"]

    @pytest.mark.parametrize(
        "endpoint",
        ["/", "/auth/login.html", "/quiz/test/all", "/examples", "/home", "/course"],
    )
    def test_pages_availability(self, endpoint: str, requester: Session):
        """Checks accessibility for specified pages"""
        url = f"{MAIN_PAGE}{endpoint}"
        status_code = requester.get(url).status_code

        assert status_code == 200
