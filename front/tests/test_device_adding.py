import pytest
from selenium.webdriver.common.by import By
from env.locators import DEVICE_BUTTON_CLASSES, DEVICE_BUTTON_SELECTORS
from conftest import MiminetTester
from env.networks import MiminetTestNetwork


class TestDeviceButtons:
    @pytest.fixture(scope="class")
    def network(self, selenium: MiminetTester):
        empty_network = MiminetTestNetwork(selenium)

        yield empty_network

        empty_network.delete()

    @pytest.mark.parametrize(
        "element_selector,element_name,current_node",
        zip(
            DEVICE_BUTTON_SELECTORS,
            DEVICE_BUTTON_CLASSES,
            range(len(DEVICE_BUTTON_SELECTORS)),
        ),
    )
    def test_element_adding(
        self,
        selenium: MiminetTester,
        network: MiminetTestNetwork,
        element_selector: str,
        element_name: str,
        current_node: int,
    ):
        network_device_button = selenium.find_element(By.CSS_SELECTOR, element_selector)

        # add every device to same position
        network.add_node(network_device_button, 50, 50)

        # get element from field
        node_name = selenium.execute_script(f"return nodes[{current_node}].classes[0]")

        assert node_name == element_name
