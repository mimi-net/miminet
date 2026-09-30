import pytest
from playwright.sync_api import Page

from conftest import WAIT_UNTIL
from utils.checkers import TestNetworkComparator
from utils.locators import Location
from utils.networks import MiminetTestNetwork, NodeType


class TestPingAndCopy:
    @pytest.fixture(scope="class")
    def network(self, authorized_page: Page):
        network = MiminetTestNetwork(authorized_page)

        host1_id = network.add_node(NodeType.Host)
        host2_id = network.add_node(NodeType.Host)

        # edge between hosts
        network.add_edge(host1_id, host2_id)

        # configure host 1
        config0 = network.open_node_config(host1_id)
        config0.fill_link("192.168.1.1", 24)
        config0.add_jobs(
            1,
            {Location.Network.ConfigPanel.Host.Job.PING_FIELD.selector: "192.168.1.2"},
        )
        config0.submit()

        # configure host 2
        config1 = network.open_node_config(host2_id)
        config1.fill_link("192.168.1.2", 24)
        config1.submit()

        yield network

        network.delete()

    def test_ping(self, authorized_page: Page, network: MiminetTestNetwork):
        assert TestNetworkComparator.compare_nodes(network.nodes, self.JSON_NODES)
        assert TestNetworkComparator.compare_edges(network.edges, self.JSON_EDGES)
        assert TestNetworkComparator.compare_jobs(network.jobs, self.JOBS)

    def test_ping_network_copy(
        self, authorized_page: Page, network: MiminetTestNetwork
    ):
        authorized_page.goto(network.url)

        nodes = network.nodes
        edges = network.edges
        jobs = network.jobs

        authorized_page.click(Location.Network.TopButton.COPY.selector)

        # The dialog is addressed by its own id rather than by the positional
        # xpath the Selenium suite uses: the copy modal is one of several
        # dialogs appended to <body>, so its index shifts as dialogs are added.
        # The button is picked by its label rather than by index -- the first
        # button inside the dialog is the close cross, not this one.
        authorized_page.click("#ModalCopy button:has-text('Перейти к редактированию')")

        # The click navigates to the copy; wait for that before reading the URL.
        # wait_until matches the conftest default -- the editor page keeps `load`
        # pending far longer than the DOM takes to be ready.
        authorized_page.wait_for_url(
            lambda url: url != network.url, wait_until=WAIT_UNTIL
        )

        copy_network = MiminetTestNetwork(authorized_page, authorized_page.url)

        assert copy_network.url != network.url, "Redirecting wasn't completed"
        assert TestNetworkComparator.compare_nodes(nodes, copy_network.nodes)
        assert TestNetworkComparator.compare_edges(edges, copy_network.edges)
        assert TestNetworkComparator.compare_jobs(jobs, copy_network.jobs)

        copy_network.delete()
        authorized_page.goto(network.url)

    JSON_NODES = [
        {
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
        },
        {
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
        },
    ]

    JSON_EDGES = [
        {
            "data": {
                "id": "edge_m3x96snujpyaycfix1",
                "source": "host_1",
                "target": "host_2",
            }
        }
    ]

    JOBS = [
        {
            "arg_1": "192.168.1.2",
            "host_id": "host_1",
            "id": "c6196d5b58d54d30b2cc98af5e8e9d33",
            "job_id": 1,
            "level": 0,
            "print_cmd": "ping -c 1 192.168.1.2",
        }
    ]
