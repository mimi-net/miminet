from random import randint, randrange
import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver import Chrome
from selenium.webdriver import ActionChains
from conftest import DEVICE_BUTTON_XPATHS, DEVICE_BUTTON_CLASSES, device_button


def get_current_node(selenium, device_class):
    nodes = selenium.execute_script("return nodes")
    filtered_nodes = list(
        filter(lambda node: node["classes"][0] == device_class, nodes)
    )

    assert len(filtered_nodes) == 1, f"Can't find device node for {device_class}!!!"

    device_node = filtered_nodes[0]

    return device_node


def open_config(selenium, device_node):
    device_class = device_node["classes"][0]

    if device_class == device_button.host_class:
        selenium.execute_script(f"ShowHostConfig({device_node})")
    elif device_class == device_button.switch_class:
        selenium.execute_script(f"ShowSwitchConfig({device_node})")
    elif device_class == device_button.hub_class:
        selenium.execute_script(f"ShowHubConfig({device_node})")
    elif device_class == device_button.router_class:
        selenium.execute_script(f"ShowRouterConfig({device_node})")
    elif device_class == device_button.server_class:
        selenium.execute_script(f"ShowServerConfig({device_node})")
    else:
        raise Exception("Can't find device type !!!")


class TestDeviceConfigure:

    @pytest.fixture(scope="class")
    def network_with_elements_url(self, selenium: Chrome, empty_network_url: str):
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

            x, y = randint(0, width) - offset_x, randint(0, height) - offset_y

            actions_chain = ActionChains(selenium)

            actions_chain.click_and_hold(element)
            actions_chain.move_to_element_with_offset(target, x, y)
            actions_chain.release()
            actions_chain.perform()

        return network_url

    @pytest.mark.parametrize(
        "device_class",
        (DEVICE_BUTTON_CLASSES),
    )
    def test_device_name_change(
        self, selenium: Chrome, network_with_elements_url: str, device_class: str
    ):
        """Just change the name of the device"""
        selenium.get(network_with_elements_url)

        device_node = get_current_node(selenium, device_class)

        open_config(selenium, device_node)

        # open config form

        name_field_xpath = "/html/body/main/section/div/div/div[3]/form/div[1]/input"
        confirm_button_xpath = "/html/body/main/section/div/div/div[3]/form/button"

        new_device_name = "new name!"
        # enter name
        name_field = selenium.find_element(By.XPATH, name_field_xpath)
        name_field.clear()
        name_field.send_keys(new_device_name)
        # press confirm button
        selenium.find_element(By.XPATH, confirm_button_xpath).click()

        device_node = get_current_node(selenium, device_class)

        assert device_node["config"]["label"] == new_device_name

    @pytest.mark.parametrize(
        "device_class",
        (DEVICE_BUTTON_CLASSES),
    )
    def test_device_name_change_to_long(
        self, selenium: Chrome, network_with_elements_url: str, device_class: str
    ):
        """Change device name to long string and checks if it has been cut"""
        selenium.get(network_with_elements_url)

        device_node = get_current_node(selenium, device_class)

        open_config(selenium, device_node)

        # open config form

        name_field_xpath = "/html/body/main/section/div/div/div[3]/form/div[1]/input"
        confirm_button_xpath = "/html/body/main/section/div/div/div[3]/form/button"

        new_device_name = 'a' * 100
        # enter name
        name_field = selenium.find_element(By.XPATH, name_field_xpath)
        name_field.clear()
        name_field.send_keys(new_device_name)
        # press confirm button
        selenium.find_element(By.XPATH, confirm_button_xpath).click()

        device_node = get_current_node(selenium, device_class)

        assert device_node["config"]["label"] != new_device_name
