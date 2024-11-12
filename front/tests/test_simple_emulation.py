import pytest
from conftest import MiminetTester
from env.networks import MiminetTestNetwork
from selenium.webdriver.common.by import By
from env.locators import (
    CONFIG_IP_ADDRESS_FIELD_XPATH,
    CONFIG_MASK_FIELD_XPATH,
    CONFIG_JOB_SELECT_XPATH,
    JOB_FIELD_1_XPATH,
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

        # edge between hosts
        network.add_edge(network.nodes[0], network.nodes[1])

        # configure host 1
        network.open_node_config(network.nodes[0])
        self.configure_address(selenium, "192.168.1.1", "24")
        self.add_ping_job(selenium, "192.168.1.2")

        # configure host 2
        network.open_node_config(network.nodes[1])
        self.configure_address(selenium, "192.168.1.2", "24")

        yield network

        network.delete()

    def configure_address(self, selenium: MiminetTester, ip: str, mask: str):
        selenium.find_element(By.XPATH, CONFIG_IP_ADDRESS_FIELD_XPATH).send_keys(ip)
        selenium.find_element(By.XPATH, CONFIG_MASK_FIELD_XPATH).send_keys(mask)

        selenium.find_element(By.XPATH, CONFIG_CONFIRM_BUTTON_XPATH).click()
        selenium.wait_until_text(
            By.XPATH, CONFIG_CONFIRM_BUTTON_XPATH, CONFIG_CONFIRM_BUTTON_TEXT
        )

    def add_ping_job(self, selenium: MiminetTester, ip: str):
        ADDED_JOB_XPATH = "/html/body/main/section/div/div/div[3]/form/ul/li/small"

        selenium.select_by_value(By.XPATH, CONFIG_JOB_SELECT_XPATH, 1)
        selenium.find_element(By.XPATH, JOB_FIELD_1_XPATH).send_keys(ip)
        selenium.find_element(By.XPATH, JOB_FIELD_1_XPATH).send_keys(Keys.RETURN)
        selenium.wait_until_appear(By.XPATH, ADDED_JOB_XPATH, timeout=60)

    def test_1(self, selenium: MiminetTester, network: MiminetTestNetwork):
        selenium.find_element(By.XPATH, EMULATE_BUTTON_XPATH).click()
        selenium.wait_until_appear(By.CSS_SELECTOR, EMULATE_PLAYER_PAUSE_SELECTOR, 30)

        packets = selenium.execute_script("return packets")

        assert len(packets) == 4
