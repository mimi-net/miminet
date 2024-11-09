import pytest
from selenium.webdriver.common.by import By
from env.locators import (
    DEVICE_BUTTON_XPATHS,
    DEVICE_BUTTON_CLASSES,
)
from conftest import MiminetTester
from env.networks import MiminetTestNetwork


class TestDeviceButtons:
    @pytest.fixture(scope="class")
    def empty_network(self, selenium: MiminetTester):
        empty_network = MiminetTestNetwork(selenium)

        yield empty_network.url

        empty_network.delete()

    @pytest.mark.parametrize(
        "element_xpath,element_name,current_node",
        zip(
            DEVICE_BUTTON_XPATHS,
            DEVICE_BUTTON_CLASSES,
            range(len(DEVICE_BUTTON_XPATHS)),
        ),
    )
    def test_element_adding(
        self,
        selenium: MiminetTester,
        empty_network: str,
        element_xpath: str,
        element_name: str,
        current_node: int,
    ):
        target_xpath = "/html/body/main/section/div/div/div[2]/div/div/canvas[2]"

        selenium.get(empty_network)

        network_device_button = selenium.find_element(By.XPATH, element_xpath)
        target_panel = selenium.find_element(By.XPATH, target_xpath)

        selenium.drag_and_drop(network_device_button, target_panel, 100, 100)

        # get element from field
        script_res = selenium.execute_script(f"return nodes[{current_node}].classes[0]")

        assert script_res == element_name
