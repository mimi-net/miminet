from selenium.webdriver.common.by import By
from env.locators import (
    DEVICE_BUTTON_XPATHS,
    network_top_button,
    NETWORK_PANEL_XPATH,
)
from conftest import HOME_PAGE, MiminetTester
import random


class MiminetTestNetwork:
    """
    Represents a Miminet network created for testing purposes.
    You can easily configure your test networks using this class.
    """
    def __init__(self, selenium: MiminetTester):
        self.__selenium = selenium
        self.__build_empty_network()

    @property
    def url(self):
        return self.__url

    def __build_empty_network(self):
        """Create new network and clear it after use.

        Returns:
        (str) : Network URL
        """
        new_network_button_xpath = "/html/body/section/div/div/div[1]"

        self.__selenium.get(HOME_PAGE)
        self.__selenium.find_element(By.XPATH, new_network_button_xpath).click()

        self.__url = self.__selenium.current_url

    def scatter_devices(self):
        """Randomly add each network device to network."""
        self.__selenium.get(self.__url)
        panel = self.__selenium.find_element(By.XPATH, NETWORK_PANEL_XPATH)

        # calculate offset of coordinates inside panel

        width, height = int(panel.rect["width"]), int(panel.rect["height"])
        target_x, target_y = int(panel.rect["x"]), int(panel.rect["y"])

        center_x, center_y = target_x + width / 2, target_y + height / 2
        offset_x, offset_y = center_x - target_x, center_y - target_y

        for button_xpath in DEVICE_BUTTON_XPATHS:
            device = self.__selenium.find_element(By.XPATH, button_xpath)

            x, y = (
                random.randint(0, width) - offset_x,
                random.randint(0, height) - offset_y,
            )

            self.__selenium.drag_and_drop(device, panel, x, y)

    def delete(self):
        confirm_button_xpath = "/html/body/div[2]/div/div/div[2]/button[1]"

        self.__selenium.get(self.__url)

        self.__selenium.find_element(By.XPATH, network_top_button.options_xpath).click()

        self.__selenium.wait_and_click(By.XPATH, network_top_button.delete_xpath)
        self.__selenium.wait_and_click(By.XPATH, confirm_button_xpath)


class MiminetTestArea:
    """
    Represents a test area within a Mininet network.
    Provide access to its nodes and edges and methods for device configuring.
    """
    def __init__(self, selenium: MiminetTester, network_url: str):
        self.__selenium = selenium
        
        selenium.get(network_url)
            

    @property
    def nodes(self) -> dict:
        return self.__selenium.execute_script("return nodes")

    @property
    def edges(self) -> dict:
        return self.__selenium.execute_script("return edges")