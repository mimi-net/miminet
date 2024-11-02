import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver import Chrome
import typing


class TestNetworkMenu:
    @pytest.fixture(scope="session")
    def home_page(self, main_page):
        return f'{main_page}/home'
    
    @pytest.fixture(scope="class")
    def new_empty_network(self, selenium: Chrome, home_page: str):
        """create 1 new network (same for all tests in this class)"""
        selenium.get(home_page)

        first_network_xpath = '/html/body/section/div/div/div[1]'

        selenium.find_element(By.XPATH, first_network_xpath).click()

        return selenium.current_url

    def test_my_networks_button_press(self, selenium: Chrome, main_page: str):
        """Checks if it is possible to get to the network selection menu"""
        selenium.get(main_page)

        my_networks_button_path = '/html/body/nav/div/div/li[3]/a'

        selenium.find_element(By.XPATH, my_networks_button_path).click()

        assert selenium.current_url == f"{main_page}/home"

    def test_new_network_existence(self, selenium: Chrome, new_empty_network: str):
        """Checks if the created network exists"""
        selenium.get(new_empty_network) # open new network by URL

        network_name_xpath = '/html/body/nav/div/div[1]/a[3]'

        network_name = selenium.find_element(By.XPATH, network_name_xpath).text

        assert network_name == 'Новая сеть'

    def test_new_network_open(self, selenium: Chrome, home_page: str, new_empty_network: str):
        """Checks is it possible to open new network via home menu"""
        selenium.get(home_page)

        first_network_button_xpath = '/html/body/section/div/div/div[2]'

        selenium.find_element(By.XPATH, first_network_button_xpath).click()

        assert new_empty_network == selenium.current_url