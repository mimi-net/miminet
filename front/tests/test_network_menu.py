import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver import Chrome
from conftest import MiminetTester, HOME_PAGE, MAIN_PAGE
from env.networks import MiminetTestNetwork
from env.locators import Location


class TestNetworkMenu:
    @pytest.fixture(scope="class")
    def empty_network(self, selenium: MiminetTester):
        empty_network = MiminetTestNetwork(selenium)

        yield empty_network.url

        empty_network.delete()

    def test_my_networks_button_press(self, selenium: Chrome):
        """Checks if it is possible to get to the network selection menu"""
        selenium.get(MAIN_PAGE)
        selenium.find_element(
            By.CSS_SELECTOR, Location.NavigationButton.MY_NETWORKS_BUTTON.selector
        ).click()

        assert selenium.current_url == HOME_PAGE

    def test_new_network_existence(self, selenium: MiminetTester, empty_network: str):
        """Checks if the created network exists"""
        selenium.get(empty_network)  # open new network by URL
        network_name = selenium.find_element(
            By.CSS_SELECTOR, Location.Network.TITLE_LABEL.selector
        ).text

        assert network_name == "Новая сеть"

    def test_new_network_open(self, selenium: MiminetTester, empty_network: str):
        """Checks is it possible to open new network via home menu"""
        selenium.get(HOME_PAGE)
        selenium.find_element(
            By.XPATH, Location.MyNetworks.get_network_button_xpath(0)
        ).click()

        assert empty_network == selenium.current_url
