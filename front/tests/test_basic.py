import pytest
from conftest import testing_settings
from selenium.webdriver.common.by import By
from requests import Session
from selenium.webdriver import Chrome


class TestAvailability:

    def test_auth(self, selenium: Chrome, main_page: str):
        """Checks if it possible to open home page (are we authorized or not)"""
        selenium.get(f'{main_page}/home')

        assert selenium.title == "Веб-эмулятор"

    @pytest.mark.parametrize(
        "endpoint", ["/", "/auth/login.html", "/quiz/test/all", "/examples", "/home"]
    )
    def test_pages_availability(self, endpoint: str, requester: Session, main_page: str):
        """Checks accessibility for specified pages"""
        url = f"{main_page}{endpoint}"
        status_code = requester.get(url).status_code

        assert status_code == 200
