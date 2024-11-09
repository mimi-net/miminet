import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver import Chrome
from front.tests.conftest.locators import (
    DEVICE_BUTTON_XPATHS,
    DEVICE_BUTTON_CLASSES,
)
from selenium.webdriver import ActionChains


class TestDeviceButtons:
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
        selenium: Chrome,
        empty_network_url: str,
        element_xpath: str,
        element_name: str,
        current_node: int,
    ):
        target_xpath = "/html/body/main/section/div/div/div[2]/div/div/canvas[2]"

        selenium.get(empty_network_url)

        network_device_button = selenium.find_element(By.XPATH, element_xpath)
        target_panel = selenium.find_element(By.XPATH, target_xpath)

        actions_chain = ActionChains(selenium)

        actions_chain.click_and_hold(network_device_button)
        actions_chain.move_to_element_with_offset(target_panel, 100, 100)
        actions_chain.release()
        actions_chain.perform()

        # get element from field
        script_res = selenium.execute_script(f"return nodes[{current_node}].classes[0]")

        assert script_res == element_name
