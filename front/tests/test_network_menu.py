import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver import Chrome
from conftest import MiminetTester, HOME_PAGE, MAIN_PAGE
from env.networks import MiminetTestNetwork
from env.locators import (
    MY_NETWORK_BUTTON_XPATH,
    NETWORK_NAME_LABEL_XPATH,
    FIRST_NETWORK_BUTTON_XPATH,
)


class TestNetworkMenu:
    @pytest.fixture(scope="class")
    def empty_network(self, selenium: MiminetTester):
        empty_network = MiminetTestNetwork(selenium)

        yield empty_network.url

        empty_network.delete()

    def test_my_networks_button_press(self, selenium: Chrome):
        """Checks if it is possible to get to the network selection menu"""
        selenium.get(MAIN_PAGE)
        selenium.find_element(By.XPATH, MY_NETWORK_BUTTON_XPATH).click()

        assert selenium.current_url == HOME_PAGE

    def test_new_network_existence(self, selenium: MiminetTester, empty_network: str):
        """Checks if the created network exists"""
        selenium.get(empty_network)  # open new network by URL
        network_name = selenium.find_element(By.XPATH, NETWORK_NAME_LABEL_XPATH).text

        assert network_name == "Новая сеть"

    def test_new_network_open(self, selenium: MiminetTester, empty_network: str):
        """Checks is it possible to open new network via home menu"""
        selenium.get(HOME_PAGE)
        selenium.find_element(By.XPATH, FIRST_NETWORK_BUTTON_XPATH).click()

        assert empty_network == selenium.current_url
