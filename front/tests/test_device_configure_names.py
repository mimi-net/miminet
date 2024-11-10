import pytest
from selenium.webdriver import Chrome
from selenium.webdriver.common.by import By
from conftest import MiminetTester
from env.locators import (
    DEVICE_BUTTON_CLASSES,
    device_button,
    CONFIG_NAME_FIELD_XPATH,
    CONFIG_CONFIRM_BUTTON_XPATH
)
from env.networks import MiminetTestNetwork


def get_current_node(selenium: MiminetTester, device_class: str):
    nodes = selenium.execute_script("return nodes")
    filtered_nodes = list(
        filter(lambda node: node["classes"][0] == device_class, nodes)
    )

    assert len(filtered_nodes) == 1, f"Can't find device node for {device_class}!!!"

    device_node = filtered_nodes[0]

    return device_node


def open_config(selenium: MiminetTester, device_node: dict):
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
    def network_with_elements(self, selenium: MiminetTester):
        network = MiminetTestNetwork(selenium)
        network.scatter_devices()

        yield network.url

        network.delete()

    @pytest.mark.parametrize(
        "device_class",
        (DEVICE_BUTTON_CLASSES),
    )
    def test_device_name_change(
        self, selenium: MiminetTester, network_with_elements: str, device_class: str
    ):
        """Just change the name of the device"""
        selenium.get(network_with_elements)

        device_node = get_current_node(selenium, device_class)

        open_config(selenium, device_node)

        new_device_name = "new name!"
        # enter name
        name_field = selenium.find_element(By.XPATH, CONFIG_NAME_FIELD_XPATH)
        name_field.clear()
        name_field.send_keys(new_device_name)
        # press confirm button
        selenium.find_element(By.XPATH, CONFIG_CONFIRM_BUTTON_XPATH).click()

        device_node = get_current_node(selenium, device_class)

        assert device_node["config"]["label"] == new_device_name

    @pytest.mark.parametrize(
        "device_class",
        (DEVICE_BUTTON_CLASSES),
    )
    def test_device_name_change_to_long(
        self, selenium: Chrome, network_with_elements: str, device_class: str
    ):
        """Change device name to long string and checks if it has been cut"""
        selenium.get(network_with_elements)

        device_node = get_current_node(selenium, device_class)

        open_config(selenium, device_node)

        # open config form

        new_device_name = "a" * 100
        # enter name
        name_field = selenium.find_element(By.XPATH, CONFIG_NAME_FIELD_XPATH)
        name_field.clear()
        name_field.send_keys(new_device_name)
        # press confirm button
        selenium.find_element(By.XPATH, CONFIG_CONFIRM_BUTTON_XPATH).click()

        device_node = get_current_node(selenium, device_class)

        assert device_node["config"]["label"] != new_device_name
