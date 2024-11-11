import pytest
from selenium.webdriver import Chrome
from selenium.webdriver.common.by import By
from conftest import MiminetTester
from env.locators import (
    CONFIG_CONFIRM_BUTTON_TEXT,
    CONFIG_PANEL_XPATH,
    DEVICE_BUTTON_CLASSES,
    device_button,
    CONFIG_NAME_FIELD_XPATH,
    CONFIG_CONFIRM_BUTTON_XPATH,
)
from env.networks import MiminetTestNetwork


class TestDeviceNameChange:
    @pytest.fixture(scope="class")
    def network_with_elements(self, selenium: MiminetTester):
        network = MiminetTestNetwork(selenium)
        network.scatter_devices()

        yield network

        network.delete()

    @pytest.mark.parametrize(
        "device_class",
        (DEVICE_BUTTON_CLASSES),
    )
    def test_device_name_change(
        self,
        selenium: MiminetTester,
        network_with_elements: MiminetTestNetwork,
        device_class: str,
    ):
        """Just change the name of the device"""
        selenium.get(network_with_elements.url)

        device_node = network_with_elements.get_nodes_by_class(device_class)[0]
        network_with_elements.open_node_config(device_node)

        new_device_name = "new name!"
        # enter name
        name_field = selenium.find_element(By.XPATH, CONFIG_NAME_FIELD_XPATH)
        name_field.clear()
        name_field.send_keys(new_device_name)
        # press confirm button
        selenium.find_element(By.XPATH, CONFIG_CONFIRM_BUTTON_XPATH).click()

        selenium.wait_until_text(
            By.XPATH, CONFIG_CONFIRM_BUTTON_XPATH, CONFIG_CONFIRM_BUTTON_TEXT
        )

        device_node = network_with_elements.get_nodes_by_class(device_class)[0]

        assert device_node["config"]["label"] == new_device_name

    @pytest.mark.parametrize(
        "device_class",
        (DEVICE_BUTTON_CLASSES),
    )
    def test_device_name_change_to_long(
        self,
        selenium: MiminetTester,
        network_with_elements: MiminetTestNetwork,
        device_class: str,
    ):
        """Change device name to long string and checks if it has been cut"""
        selenium.get(network_with_elements.url)

        device_node = network_with_elements.get_nodes_by_class(device_class)[0]

        network_with_elements.open_node_config(device_node)

        # open config form

        new_device_name = "a" * 100
        # enter name
        name_field = selenium.find_element(By.XPATH, CONFIG_NAME_FIELD_XPATH)
        name_field.clear()
        name_field.send_keys(new_device_name)
        # press confirm button
        selenium.find_element(By.XPATH, CONFIG_CONFIRM_BUTTON_XPATH).click()

        selenium.wait_until_text(
            By.XPATH, CONFIG_CONFIRM_BUTTON_XPATH, CONFIG_CONFIRM_BUTTON_TEXT
        )

        device_node = network_with_elements.get_nodes_by_class(device_class)[0]

        assert device_node["config"]["label"] != new_device_name
