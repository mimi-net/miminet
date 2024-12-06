import pytest
from conftest import MiminetTester
from env.networks import (
    NodeConfig,
    NodeType,
    MiminetTestNetwork,
    compare_nodes,
    compare_edges,
)
from env.locators import Locator


class TestTcp:
    """
    This test build complex network,
    using switch, hub, tcp server and host.

    It checks not only the TCP connection setup,
    but also the default gateway settings.
    """

    @pytest.fixture(scope="class")
    def network(self, selenium: MiminetTester):
        network = MiminetTestNetwork(selenium)

        # nodes
        network.add_node(NodeType.Host, x=20, y=50)
        network.add_node(NodeType.Switch, x=35, y=75)
        network.add_node(NodeType.Router, x=50, y=50)
        network.add_node(NodeType.Hub, x=65, y=75)
        network.add_node(NodeType.Server, x=80, y=50)

        # edges
        network.add_edge(0, 1)  # host -> switch
        network.add_edge(1, 2)  # switch -> router
        network.add_edge(2, 3)  # switch -> hub
        network.add_edge(3, 4)  # hub -> server

        # config host
        host_config: NodeConfig = network.open_node_config(0)
        host_config.fill_link("192.168.1.1", 24)
        host_config.fill_default_gw("192.168.1.2")
        host_config.add_job(
            4,
            {
                Locator.Network.ConfigPanel.Host.Job.TCP_VOLUME_IN_BYTES_FIELD[
                    "selector"
                ]: "65535",
                Locator.Network.ConfigPanel.Host.Job.TCP_IP_FIELD[
                    "selector"
                ]: "10.0.0.1",
                Locator.Network.ConfigPanel.Host.Job.TCP_PORT_FIELD["selector"]: "3000",
            },
        )
        host_config.submit()

        # config router
        router_config: NodeConfig = network.open_node_config(2)
        router_config.fill_link("192.168.1.2", 24, link_id=0)
        router_config.fill_link("10.0.0.2", 24, link_id=1)
        router_config.submit()

        # config server
        server_config: NodeConfig = network.open_node_config(4)
        server_config.fill_link("10.0.0.1", 24)
        server_config.fill_default_gw("10.0.0.2")
        server_config.add_job(
            201,
            {
                Locator.Network.ConfigPanel.Server.Job.TCP_IP_FIELD[
                    "selector"
                ]: "10.0.0.1",
                Locator.Network.ConfigPanel.Server.Job.TCP_PORT_FIELD[
                    "selector"
                ]: "3000",
            },
        )
        server_config.submit()

        # finish
        yield network

        network.delete()

    def test_ping_emulation(self, selenium: MiminetTester, network: MiminetTestNetwork):
        selenium.save_screenshot("1.png")
        assert compare_nodes(JSON_NODES, network.nodes)
        assert compare_edges(JSON_EDGES, network.edges)


JSON_NODES = [
    {
        "classes": ["host"],
        "config": {"default_gw": "192.168.1.2", "label": "host_1", "type": "host"},
        "data": {"id": "host_1", "label": "host_1"},
        "interface": [
            {
                "connect": "edge_m4d8zjgq9irc5sosvnf",
                "id": "iface_72076251",
                "ip": "192.168.1.1",
                "name": "iface_72076251",
                "netmask": 24,
            }
        ],
        "position": {"x": 81.0374984741211, "y": 75},
    },
    {
        "classes": ["l2_switch"],
        "config": {"label": "l2sw1", "stp": 0, "type": "l2_switch"},
        "data": {"id": "l2sw1", "label": "l2sw1"},
        "interface": [
            {
                "connect": "edge_m4d1o9tpdgzqjbt4wze",
                "id": "l2sw1_2",
                "name": "l2sw1_2",
                "type_connection": None,
                "vlan": None,
            },
            {
                "connect": "edge_m4d8zjgq9irc5sosvnf",
                "id": "l2sw1_3",
                "name": "l2sw1_3",
                "type_connection": None,
                "vlan": None,
            },
        ],
        "position": {"x": 131.54959955491898, "y": 141.99415120802044},
    },
    {
        "classes": ["l3_router"],
        "config": {"default_gw": "", "label": "router_1", "type": "router"},
        "data": {"id": "router_1", "label": "router_1"},
        "interface": [
            {
                "connect": "edge_m4d1o9tpdgzqjbt4wze",
                "id": "iface_80424814",
                "ip": "192.168.1.2",
                "name": "iface_80424814",
                "netmask": 24,
            },
            {
                "connect": "edge_m4d1pvjr9u4htwjbced",
                "id": "iface_14250267",
                "ip": "10.0.0.2",
                "name": "iface_14250267",
                "netmask": 24,
            },
        ],
        "position": {"x": 180.5374984741211, "y": 68.30000305175781},
    },
    {
        "classes": ["l1_hub"],
        "config": {"label": "l1hub1", "type": "l1_hub"},
        "data": {"id": "l1hub1", "label": "l1hub1"},
        "interface": [
            {
                "connect": "edge_m4d1pvjr9u4htwjbced",
                "id": "l1hub1_1",
                "name": "l1hub1_1",
            },
            {
                "connect": "edge_m4d1tqljkagg89ugwma",
                "id": "l1hub1_2",
                "name": "l1hub1_2",
            },
        ],
        "position": {"x": 240.81154083854386, "y": 138.32973441098713},
    },
    {
        "classes": ["server"],
        "config": {"default_gw": "10.0.0.2", "label": "server_1", "type": "server"},
        "data": {"id": "server_1", "label": "server_1"},
        "interface": [
            {
                "connect": "edge_m4d1tqljkagg89ugwma",
                "id": "iface_42385308",
                "ip": "10.0.0.1",
                "name": "iface_42385308",
                "netmask": 24,
            }
        ],
        "position": {"x": 294.5622719375413, "y": 58.129486133684594},
    },
]

JSON_EDGES = [
    {
        "data": {
            "id": "edge_m4d8zjgq9irc5sosvnf",
            "source": "host_1",
            "target": "l2sw1",
        }
    },
    {
        "data": {
            "id": "edge_m4d1o9tpdgzqjbt4wze",
            "source": "l2sw1",
            "target": "router_1",
        }
    },
    {
        "data": {
            "id": "edge_m4d1pvjr9u4htwjbced",
            "source": "router_1",
            "target": "l1hub1",
        }
    },
    {
        "data": {
            "id": "edge_m4d1tqljkagg89ugwma",
            "source": "l1hub1",
            "target": "server_1",
        }
    },
]
