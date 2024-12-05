import pytest
from conftest import MiminetTester
from env.networks import MiminetTestNetwork, compare_nodes, compare_edges
from selenium.webdriver.common.by import By
from env.locators import Locator
from selenium.webdriver.common.keys import Keys


class TestSimpleEmulation:
    @pytest.fixture(scope="class")
    def network(self, selenium: MiminetTester):
        network = MiminetTestNetwork(selenium)

        host_button = selenium.find_element(By.CSS_SELECTOR, Locator.Network.DevicePanel.HOST['selector'])

        network.add_node(host_button)
        network.add_node(host_button)

        # edge between hosts
        network.add_edge(network.nodes[0], network.nodes[1])

        # configure host 1
        network.fill_link("192.168.1.1", "24", node=network.nodes[0])
        self.add_ping_job(selenium, "192.168.1.2")

        # configure host 2
        network.fill_link("192.168.1.2", "24", node=network.nodes[1])

        yield network

        network.delete()

    def add_ping_job(self, selenium: MiminetTester, ip: str):
        selenium.select_by_value(By.XPATH, Locator.Network.ConfigPanel.JOB_SELECT['xpath'], 1)

        PING_IP = Locator.Network.ConfigPanel.Job.PING_FIELD['selector']
        
        selenium.find_element(By.CSS_SELECTOR, PING_IP).send_keys(ip)
        selenium.find_element(By.CSS_SELECTOR, PING_IP).send_keys(Keys.RETURN)
        selenium.wait_until_disappear(By.CSS_SELECTOR, PING_IP)

    def test_ping_emulation(self, selenium: MiminetTester, network: MiminetTestNetwork):
        assert compare_nodes(network.nodes, self.JSON_NODES)
        assert compare_edges(network.edges, self.JSON_EDGES)

    def test_ping_network_copy(
        self, selenium: MiminetTester, network: MiminetTestNetwork
    ):
        selenium.get(network.url)

        nodes = network.nodes
        edges = network.edges

        selenium.find_element(By.CSS_SELECTOR, Locator.Network.TopButton.COPY['selector']).click()
        selenium.wait_until_appear(By.XPATH, Locator.Network.MODAL_DIALOG['xpath'])

        selenium.find_element(By.XPATH, Locator.Network.TopButton.ModalButton.GO_TO_EDITING['xpath']).click()

        copy_network = MiminetTestNetwork(selenium, selenium.current_url)

        assert selenium.current_url != network.url, "Redirecting wasn't completed"
        assert compare_nodes(nodes, copy_network.nodes)
        assert compare_edges(edges, copy_network.edges)

        selenium.get(network.url)

    JSON_NODES = {
        "classes": ["host"],
        "config": {"default_gw": "", "label": "host_1", "type": "host"},
        "data": {"id": "host_1", "label": "host_1"},
        "interface": [
            {
                "connect": "edge_m3x96snujpyaycfix1",
                "id": "iface_86881674",
                "ip": "192.168.1.1",
                "name": "iface_86881674",
                "netmask": 24,
            }
        ],
        "position": {"x": 58.537498474121094, "y": 99},
    }, {
        "classes": ["host"],
        "config": {"default_gw": "", "label": "host_2", "type": "host"},
        "data": {"id": "host_2", "label": "host_2"},
        "interface": [
            {
                "connect": "edge_m3x96snujpyaycfix1",
                "id": "iface_77541826",
                "ip": "192.168.1.2",
                "name": "iface_77541826",
                "netmask": 24,
            }
        ],
        "position": {"x": 158.5374984741211, "y": 111},
    }

    JSON_EDGES = [
        {
            "data": {
                "id": "edge_m3x96snujpyaycfix1",
                "source": "host_1",
                "target": "host_2",
            }
        }
    ]
