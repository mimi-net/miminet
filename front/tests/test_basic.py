import pytest
from conftest import testing_settings
from selenium.webdriver.common.by import By

class TestAvailability:

    def test_auth(self, selenium):
        selenium.get(testing_settings.miminet_address)
        selenium.find_element(By.XPATH, "/html/body/nav/div/div/li[3]").click()

        assert selenium.title == "Веб-эмулятор"
        assert selenium.current_url == testing_settings.miminet_address + "/home"

    @pytest.mark.parametrize(
        "endpoint", ["/", "/auth/login.html", "/quiz/test/all", "/examples", "/home"]
    )
    def test_pages_availability(self, testing_session, endpoint):
        url = f"{testing_settings.miminet_address}{endpoint}"
        status_code = testing_session.get(url).status_code

        assert status_code == 200
