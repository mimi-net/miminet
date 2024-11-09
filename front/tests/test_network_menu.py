import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver import Chrome
from conftest.environment_setup import (
    MiminetTester,
    HOME_PAGE,
    MAIN_PAGE,
    selenium,
    chrome_driver,
    requester,
)
from conftest.networks import MiminetTestNetwork


class TestNetworkMenu:
    @pytest.fixture(scope="class")
    def empty_network(self, selenium: MiminetTester):
        empty_network = MiminetTestNetwork(selenium)

        return empty_network.url

    def test_my_networks_button_press(self, selenium: Chrome):
        """Checks if it is possible to get to the network selection menu"""
        my_networks_button_path = "/html/body/nav/div/div/li[3]/a"

        selenium.get(MAIN_PAGE)
        selenium.find_element(By.XPATH, my_networks_button_path).click()

        assert selenium.current_url == HOME_PAGE

    def test_new_network_existence(self, selenium: MiminetTester, empty_network: str):
        """Checks if the created network exists"""
        network_name_xpath = "/html/body/nav/div/div[1]/a[3]"

        selenium.get(empty_network)  # open new network by URL
        network_name = selenium.find_element(By.XPATH, network_name_xpath).text

        assert network_name == "Новая сеть"

    def test_new_network_open(self, selenium: MiminetTester, empty_network: str):
        """Checks is it possible to open new network via home menu"""
        first_network_button_xpath = "/html/body/section/div/div/div[2]"

        selenium.get(HOME_PAGE)
        selenium.find_element(By.XPATH, first_network_button_xpath).click()

        assert empty_network == selenium.current_url
