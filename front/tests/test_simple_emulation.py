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
    NETWORK_COPY_BUTTON_XPATH,
    MODAL_DIALOG_XPATH,
    GO_TO_EDITING_BUTTON_XPATH,
)
from env.locators import device_button
from selenium.webdriver.common.keys import Keys


class TestSimpleEmulation:
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
        selenium.wait_until_appear(By.XPATH, ADDED_JOB_XPATH)

    def test_ping_emulation(self, selenium: MiminetTester, network: MiminetTestNetwork):
        packets = network.run_emulation()

        assert len(packets) == 4  # TODO change to something better???

    def test_ping_network_copy(
        self, selenium: MiminetTester, network: MiminetTestNetwork
    ):
        selenium.get(network.url)

        nodes = network.nodes
        edges = network.edges

        selenium.find_element(By.XPATH, NETWORK_COPY_BUTTON_XPATH).click()
        selenium.wait_until_appear(By.XPATH, MODAL_DIALOG_XPATH)

        selenium.find_element(By.XPATH, GO_TO_EDITING_BUTTON_XPATH).click()

        copy_network = MiminetTestNetwork(selenium, selenium.current_url)
        packets = copy_network.run_emulation()

        assert selenium.current_url != network.url, "Redirecting wasn't completed"
        assert copy_network.nodes == nodes, "Nodes don't match"
        assert copy_network.edges == edges, "Edges don't match"
        assert (
            len(packets) == 4
        ), "Emulation doesn't match"  # TODO change to something better???

        selenium.get(network.url)
