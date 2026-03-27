import pytest
from conftest import MiminetTester
from utils.networks import NodeType, MiminetTestNetwork
from utils.locators import Location
from utils.checkers import TestNetworkComparator


class TestDHCP:

    @pytest.fixture(scope="class")
    def network(self, selenium: MiminetTester):
        network = MiminetTestNetwork(selenium)

        # nodes
        network.add_node(NodeType.Host, 25, 80)  # host 1
        network.add_node(NodeType.Host, 75, 80)  # host 2
        network.add_node(NodeType.Switch, 50, 65)  # switch 1
        network.add_node(NodeType.Server, 25, 55)  # server 1

        # edges
        network.add_edge(0, 2)  # host 1 -> switch 1
        network.add_edge(1, 2)  # host 2 -> switch 1
        network.add_edge(3, 2)  # server 1 -> switch 1

        # configure hosts
        host1_iface = network.nodes[0]["interface"][0]["id"]

        host1_config = network.open_node_config(0)
        host1_config.fill_link("192.168.0.1", 24)
        host1_config.add_jobs(
            108,
            {Location.Network.ConfigPanel.Host.Job.DHCLIENT_INTF.selector: host1_iface},
        )
        host1_config.submit()

        host2_config = network.open_node_config(1)
        host2_config.fill_link("192.168.0.101", 24)
        host2_config.add_jobs(
            1,
            {
                Location.Network.ConfigPanel.Host.Job.PING_FIELD.selector: "192.168.0.100"
            },
        )
        host2_config.submit()

        # config server
        server_iface = network.nodes[3]["interface"][0]["id"]

        server_config = network.open_node_config(3)
        server_config.fill_link("192.168.0.2", 24)
        server_config.add_jobs(
            203,
            {
                Location.Network.ConfigPanel.Server.Job.DHCP_IP_RANGE_START_FIELD.selector: "192.168.0.100",
                Location.Network.ConfigPanel.Server.Job.DHCP_IP_RANGE_END_FIELD.selector: "192.168.0.100",
                Location.Network.ConfigPanel.Server.Job.DHCP_MASK_FIELD.selector: "24",
                Location.Network.ConfigPanel.Server.Job.DHCP_IP_GW_FIELD.selector: "192.168.0.3",
                Location.Network.ConfigPanel.Server.Job.DHCP_INTF.selector: server_iface,
            },
        )
        server_config.submit()

        yield network

        network.delete()

    def test_dhcp(self, selenium: MiminetTester, network: MiminetTestNetwork):
        assert TestNetworkComparator.compare_nodes(network.nodes, self.JSON_NODES)
        assert TestNetworkComparator.compare_edges(network.edges, self.JSON_EDGES)
        assert TestNetworkComparator.compare_jobs(network.jobs, self.JSON_JOBS)

    JSON_NODES = [
        {
            "classes": ["host"],
            "config": {"default_gw": "", "label": "host_1", "type": "host"},
            "data": {"id": "host_1", "label": "host_1"},
            "interface": [
                {
                    "connect": "edge_mgkzw1i1fdwkdkwsrvj",
                    "id": "iface_12223663",
                    "ip": "192.168.0.1",
                    "name": "iface_12223663",
                    "netmask": 24,
                }
            ],
            "position": {"x": 108.5, "y": 302.5},
        },
        {
            "classes": ["host"],
            "config": {"default_gw": "", "label": "host_2", "type": "host"},
            "data": {"id": "host_2", "label": "host_2"},
            "interface": [
                {
                    "connect": "edge_mgkzw2sv01immjxijw32",
                    "id": "iface_44250685",
                    "ip": "192.168.0.101",
                    "name": "iface_44250685",
                    "netmask": 24,
                }
            ],
            "position": {"x": 326.5, "y": 302.5},
        },
        {
            "classes": ["l2_switch"],
            "config": {"label": "l2sw1", "stp": 0, "type": "l2_switch"},
            "data": {"id": "l2sw1", "label": "l2sw1"},
            "interface": [
                {
                    "connect": "edge_mgkzw1i1fdwkdkwsrvj",
                    "id": "l2sw1_2",
                    "name": "l2sw1_2",
                    "type_connection": None,
                    "vlan": None,
                },
                {
                    "connect": "edge_mgkzw2sv01immjxijw32",
                    "id": "l2sw1_3",
                    "name": "l2sw1_3",
                    "type_connection": None,
                    "vlan": None,
                },
                {
                    "connect": "edge_mgkzw01cxcskdwiw8sq",
                    "id": "l2sw1_1",
                    "name": "l2sw1_1",
                    "type_connection": None,
                    "vlan": None,
                },
            ],
            "position": {"x": 217.5, "y": 243.5},
        },
        {
            "classes": ["server"],
            "config": {"default_gw": "", "label": "server_1", "type": "server"},
            "data": {"id": "server_1", "label": "server_1"},
            "interface": [
                {
                    "connect": "edge_mgkzw01cxcskdwiw8sq",
                    "id": "iface_07610054",
                    "ip": "192.168.0.2",
                    "name": "iface_07610054",
                    "netmask": 24,
                }
            ],
            "position": {"x": 326.5, "y": 204.5},
        },
    ]

    JSON_EDGES = [
        {
            "data": {
                "id": "edge_mgkzw1i1fdwkdkwsrvj",
                "source": "host_1",
                "target": "l2sw1",
                "loss_percentage": 0,
            }
        },
        {
            "data": {
                "id": "edge_mgkzw2sv01immjxijw32",
                "source": "host_2",
                "target": "l2sw1",
                "loss_percentage": 0,
            }
        },
        {
            "data": {
                "id": "edge_mgkzw01cxcskdwiw8sq",
                "source": "server_1",
                "target": "l2sw1",
                "loss_percentage": 0,
            }
        },
    ]
    JSON_JOBS = [
        {
            "id": "7538381fb4804436bccd50c4ff3416ec",
            "job_id": 108,
            "print_cmd": "dhcp client",
            "arg_1": "iface_",
            "level": 0,
            "host_id": "host_1",
        },
        {
            "id": "303bc68c571a4bd6861bab973ed61b33",
            "job_id": 1,
            "print_cmd": "ping -c 1 192.168.0.100",
            "arg_1": "192.168.0.100",
            "level": 2,
            "host_id": "host_2",
        },
        {
            "id": "859bed3f1211494d892a8b963f0eb470",
            "job_id": 203,
            "print_cmd": "dhcp ip range: 192.168.0.100,192.168.0.100/24 gw: 192.168.0.3",
            "arg_1": "192.168.0.100",
            "arg_2": "192.168.0.100",
            "arg_3": "24",
            "arg_4": "192.168.0.3",
            "arg_5": "iface_",
            "level": 2,
            "host_id": "server_1",
        },
    ]
