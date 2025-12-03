import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver import Chrome
from conftest import MiminetTester, HOME_PAGE, MAIN_PAGE
from utils.networks import MiminetTestNetwork
from utils.locators import Location


class TestNetworkMenu:
    @pytest.fixture(scope="class")
    def first_network(self, selenium: MiminetTester):
        network = MiminetTestNetwork(selenium)
        yield network.url
        network.delete()

    @pytest.fixture(scope="class")
    def second_network(self, selenium: MiminetTester):
        network = MiminetTestNetwork(selenium)
        yield network.url
        network.delete()

    def test_my_networks_button_press(self, selenium: Chrome):
        """Checks if it is possible to get to the network selection menu"""
        selenium.get(MAIN_PAGE)
        selenium.find_element(
            By.CSS_SELECTOR, Location.NavigationButton.MY_NETWORKS_BUTTON.selector
        ).click()

        assert selenium.current_url == HOME_PAGE

    def test_new_network_existence(self, selenium: MiminetTester, first_network: str):
        """Checks if the created network exists"""
        selenium.get(first_network)  # open new network by URL
        network_name = selenium.find_element(
            By.CSS_SELECTOR, Location.Network.TITLE_LABEL.selector
        ).text

        assert network_name.startswith("Сеть ")

    def test_new_network_open(self, selenium: MiminetTester, first_network: str):
        """Checks if it possible to open new network via home menu"""
        selenium.get(HOME_PAGE)
        selenium.find_element(
            By.XPATH, Location.MyNetworks.get_network_button_xpath(0)
        ).click()

        assert first_network == selenium.current_url

    def test_network_name_increments(
        self, selenium: MiminetTester, first_network: str, second_network: str
    ):
        """Checks that the second network name has an incremented number"""
        selenium.get(first_network)
        name1 = selenium.find_element(
            By.CSS_SELECTOR, Location.Network.TITLE_LABEL.selector
        ).text

        selenium.get(second_network)
        name2 = selenium.find_element(
            By.CSS_SELECTOR, Location.Network.TITLE_LABEL.selector
        ).text

        num1 = int(name1.split(" ")[-1])
        num2 = int(name2.split(" ")[-1])

        assert num2 == num1 + 1
