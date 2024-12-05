import pytest
from selenium.webdriver.common.by import By
from conftest import MiminetTester
from env.locators import Locator, DEVICE_BUTTON_CLASSES
from env.networks import MiminetTestNetwork


class TestDeviceNameChange:
    @pytest.fixture(scope="class")
    def network(self, selenium: MiminetTester):
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
        network: MiminetTestNetwork,
        device_class: str,
    ):
        """Just change the name of the device"""
        selenium.get(network.url)

        # get first node
        device_node = network.get_nodes_by_class(device_class)[0]
        network.open_node_config(device_node)

        # change device name
        new_device_name = "new name!"
        name_field = selenium.find_element(
            By.XPATH, Locator.Network.ConfigPanel.CONFIG_NAME_FIELD["xpath"]
        )
        name_field.clear()
        name_field.send_keys(new_device_name)

        # save data
        network.submit_config()

        # check that name has been updated
        device_node = network.get_nodes_by_class(device_class)[0]

        assert (
            device_node["config"]["label"] == new_device_name
        ), "Failed to change device name."

    @pytest.mark.parametrize(
        "device_class",
        (DEVICE_BUTTON_CLASSES),
    )
    def test_device_name_change_to_long(
        self,
        selenium: MiminetTester,
        network: MiminetTestNetwork,
        device_class: str,
    ):
        """Change device name to long string and checks if it has been cut"""
        device_node = network.get_nodes_by_class(device_class)[0]
        network.open_node_config(device_node)

        # change device name
        new_device_name = "a" * 100  # long name

        name_field = selenium.find_element(
            By.XPATH, Locator.Network.ConfigPanel.CONFIG_NAME_FIELD["xpath"]
        )
        name_field.clear()
        name_field.send_keys(new_device_name)

        # save changes
        network.submit_config()
        device_node = network.get_nodes_by_class(device_class)[0]

        # check that the name was cut off
        assert (
            device_node["config"]["label"] != new_device_name
        ), "The device name isn't limited in size."
