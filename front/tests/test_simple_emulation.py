import pytest
from conftest import MiminetTester
from env.networks import MiminetTestNetwork
from selenium.webdriver.common.by import By
from env.locators import (
    CONFIG_IP_ADDRESS_FIELD_XPATH,
    CONFIG_MASK_FIELD_XPATH,
    CONFIG_JOB_SELECT_XPATH,
    CONFIG_FIRST_JOB_FIELD_XPATH,
    CONFIG_CONFIRM_BUTTON_XPATH,
    CONFIG_CONFIRM_BUTTON_TEXT,
    EMULATE_BUTTON_XPATH,
    EMULATE_PLAYER_PAUSE_SELECTOR,
)
from env.locators import device_button
from selenium.webdriver.common.keys import Keys


class TestPingEmulation:
    @pytest.fixture(scope="class")
    def network(self, selenium: MiminetTester):
        network = MiminetTestNetwork(selenium)

        host_button = selenium.find_element(By.XPATH, device_button.host_xpath)

        network.add_node(host_button)
        network.add_node(host_button)

        nodes = network.nodes

        # edge between hosts
        network.add_edge(nodes[0], nodes[1])

        nodes = network.nodes
        network.open_node_config(nodes[0])

        ADDED_JOB_XPATH = "/html/body/main/section/div/div/div[3]/form/ul/li/small"

        # configure host 1
        selenium.select_by_value(By.XPATH, CONFIG_JOB_SELECT_XPATH, 1)
        selenium.find_element(By.XPATH, CONFIG_FIRST_JOB_FIELD_XPATH).send_keys(
            "192.168.1.2"
        )
        selenium.find_element(By.XPATH, CONFIG_FIRST_JOB_FIELD_XPATH).send_keys(Keys.RETURN)
        selenium.wait_until_appear(By.XPATH, ADDED_JOB_XPATH, timeout=60)

        selenium.find_element(By.XPATH, CONFIG_IP_ADDRESS_FIELD_XPATH).send_keys(
            "192.168.1.1"
        )
        selenium.find_element(By.XPATH, CONFIG_MASK_FIELD_XPATH).send_keys("24")

        selenium.find_element(By.XPATH, CONFIG_CONFIRM_BUTTON_XPATH).click()
        selenium.wait_until_text(
            By.XPATH, CONFIG_CONFIRM_BUTTON_XPATH, CONFIG_CONFIRM_BUTTON_TEXT
        )

        nodes = network.nodes
        network.open_node_config(nodes[1])

        # configure host 2
        selenium.find_element(By.XPATH, CONFIG_IP_ADDRESS_FIELD_XPATH).send_keys(
            "192.168.1.2"
        )
        selenium.find_element(By.XPATH, CONFIG_MASK_FIELD_XPATH).send_keys("24")

        selenium.find_element(By.XPATH, CONFIG_CONFIRM_BUTTON_XPATH).click()
        selenium.wait_until_text(
            By.XPATH, CONFIG_CONFIRM_BUTTON_XPATH, CONFIG_CONFIRM_BUTTON_TEXT
        )

        yield network

        network.delete()

    def test_1(self, selenium: MiminetTester, network: MiminetTestNetwork):
        selenium.find_element(By.XPATH, EMULATE_BUTTON_XPATH).click()
        selenium.wait_until_appear(By.CSS_SELECTOR, EMULATE_PLAYER_PAUSE_SELECTOR, 30)

        packets = selenium.execute_script("return packets")

        assert len(packets) == 4