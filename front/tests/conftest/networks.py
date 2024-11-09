import pytest
from environment_setup import Tester
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from locators import HOME_PAGE, DEVICE_BUTTON_XPATHS
import random


@pytest.fixture(scope="class")
def empty_network_url(selenium: Tester):
    """create 1 new network (same for all tests in this class) and clear it after use"""
    new_network_button_xpath = "/html/body/section/div/div/div[1]"

    selenium.get(HOME_PAGE)
    selenium.find_element(By.XPATH, new_network_button_xpath).click()
    network_url = selenium.current_url

    yield network_url

    delete_network(selenium, network_url)


def delete_network(selenium: Tester, network_url: str):
    options_button_xpath = "/html/body/nav/div/div[2]/a[3]/i"
    delete_network_button_xpath = "/html/body/div[1]/div/div/div[3]/button[1]"
    confirm_button_xpath = "/html/body/div[2]/div/div/div[2]/button[1]"

    selenium.get(network_url)

    selenium.find_element(By.XPATH, options_button_xpath).click()

    selenium.wait_until_can_click(By.XPATH, delete_network_button_xpath)
    selenium.wait_until_can_click(By.XPATH, confirm_button_xpath)


@pytest.fixture(scope="class")
def network_with_elements_url(selenium: Tester, empty_network_url: str):
    panel_xpath = "/html/body/main/section/div/div/div[2]/div/div/canvas[2]"
    network_url = empty_network_url

    selenium.get(network_url)

    target = selenium.find_element(By.XPATH, panel_xpath)

    # calculate offset of coordinates inside panel

    width, height = int(target.rect["width"]), int(target.rect["height"])
    target_x, target_y = int(target.rect["x"]), int(target.rect["y"])

    center_x, center_y = target_x + width / 2, target_y + height / 2
    offset_x, offset_y = center_x - target_x, center_y - target_y

    for button_xpath in DEVICE_BUTTON_XPATHS:
        element = selenium.find_element(By.XPATH, button_xpath)

        x, y = random.randint(0, width) - offset_x, random.randint(0, height) - offset_y

        actions_chain = ActionChains(selenium)

        actions_chain.click_and_hold(element)
        actions_chain.move_to_element_with_offset(target, x, y)
        actions_chain.release()
        actions_chain.perform()

    return network_url
