import pytest
from environment_setup import Tester
from selenium.webdriver.common.by import By
from locators import (
    HOME_PAGE,
    DEVICE_BUTTON_XPATHS,
    network_top_button,
    NETWORK_PANEL_XPATH,
)
import random


def delete_network(selenium: Tester, network_url: str):
    confirm_button_xpath = "/html/body/div[2]/div/div/div[2]/button[1]"

    selenium.get(network_url)

    selenium.find_element(By.XPATH, network_top_button.options_xpath).click()

    selenium.wait_and_click(By.XPATH, network_top_button.delete_xpath)
    selenium.wait_and_click(By.XPATH, confirm_button_xpath)


@pytest.fixture(scope="session")
def empty_network(selenium: Tester):
    """Create new network and clear it after use.

    Returns:
      (str) : Network URL
    """
    new_network_button_xpath = "/html/body/section/div/div/div[1]"

    selenium.get(HOME_PAGE)
    selenium.find_element(By.XPATH, new_network_button_xpath).click()
    network_url = selenium.current_url

    yield network_url

    delete_network(selenium, network_url)


@pytest.fixture(scope="session")
def network_with_elements(selenium: Tester, empty_network: str):
    """Create new network where each element is randomly located and clear it after use.

    Returns:
      (str) : Network URL
    """
    url = empty_network
    selenium.get(url)
    panel = selenium.find_element(By.XPATH, NETWORK_PANEL_XPATH)

    # calculate offset of coordinates inside panel

    width, height = int(panel.rect["width"]), int(panel.rect["height"])
    target_x, target_y = int(panel.rect["x"]), int(panel.rect["y"])

    center_x, center_y = target_x + width / 2, target_y + height / 2
    offset_x, offset_y = center_x - target_x, center_y - target_y

    for button_xpath in DEVICE_BUTTON_XPATHS:
        device = selenium.find_element(By.XPATH, button_xpath)

        x, y = random.randint(0, width) - offset_x, random.randint(0, height) - offset_y

        selenium.drag_and_drop(device, panel, x, y)

    return url
