import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver import Chrome
from conftest import HOME_PAGE, MAIN_PAGE


class TestNetworkMenu:
    @pytest.fixture(scope="class")
    def new_empty_network(self, selenium: Chrome):
        """create 1 new network (same for all tests in this class)"""
        first_network_xpath = '/html/body/section/div/div/div[1]'
        options_button_xpath = '/html/body/nav/div/div[2]/a[3]/i'
        delete_network_button_xpath = '/html/body/div[1]/div/div/div[3]/button[1]'

        selenium.get(HOME_PAGE)
        selenium.find_element(By.XPATH, first_network_xpath).click()
        network_url = selenium.current_url

        yield network_url

        selenium.get(network_url)
        selenium.find_element(By.XPATH, options_button_xpath).click()
        selenium.find_element(By.XPATH, delete_network_button_xpath).click()

    def test_my_networks_button_press(self, selenium: Chrome):
        """Checks if it is possible to get to the network selection menu"""
        my_networks_button_path = "/html/body/nav/div/div/li[3]/a"

        selenium.get(MAIN_PAGE)
        selenium.find_element(By.XPATH, my_networks_button_path).click()

        assert selenium.current_url == HOME_PAGE

    def test_new_network_existence(self, selenium: Chrome, new_empty_network: str):
        """Checks if the created network exists"""
        network_name_xpath = "/html/body/nav/div/div[1]/a[3]"

        selenium.get(new_empty_network)  # open new network by URL
        network_name = selenium.find_element(By.XPATH, network_name_xpath).text

        assert network_name == "Новая сеть"

    def test_new_network_open(
        self, selenium: Chrome, new_empty_network: str
    ):
        """Checks is it possible to open new network via home menu"""
        first_network_button_xpath = "/html/body/section/div/div/div[2]"

        selenium.get(HOME_PAGE)
        selenium.find_element(By.XPATH, first_network_button_xpath).click()

        assert new_empty_network == selenium.current_url
