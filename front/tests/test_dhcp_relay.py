import pytest
from conftest import MiminetTester
from utils.networks import NodeType, MiminetTestNetwork
from utils.locators import Location
from utils.checkers import TestNetworkComparator


class TestDHCPRelay:

    @pytest.fixture(scope="class")
    def network(self, selenium: MiminetTester):
        network = MiminetTestNetwork(selenium)

        # nodes
        network.add_node(NodeType.Host, 25, 100)  # host
        network.add_node(NodeType.Switch, 25, 50)  # switch 1
        network.add_node(NodeType.Router, 75, 0)  # router
        network.add_node(NodeType.Switch, 100, 50)  # switch 2
        network.add_node(NodeType.Server, 100, 100)  # server

        # edges
        network.add_edge(0, 1)  # host -> switch 1
        network.add_edge(1, 2)  # switch 1 -> router
        network.add_edge(2, 3)  # router -> switch 2
        network.add_edge(3, 4)  # switch 2 -> server

        # configure host
        host_iface = network.nodes[0]["interface"][0]["id"]
        host_config = network.open_node_config(0)
        host_config.add_jobs(
            108,
            {Location.Network.ConfigPanel.Host.Job.DHCLIENT_INTF.selector: host_iface},
        )
        host_config.submit()

        # configure router
        router_config = network.open_node_config(2)
        router_config.fill_link("172.16.10.3", 24)
        router_config.fill_link("192.168.10.3", 24, 1)
        router_config.add_jobs(
            204,
            {
                Location.Network.ConfigPanel.Router.Job.DHCP_RELAY_SERVER_IP_INPUT_FIELD.selector: "192.168.10.2",
                Location.Network.ConfigPanel.Router.Job.DHCP_RELAY_LISTENING_IP_INPUT_FIELD.selector: "172.16.10.3",
            },
        )
        router_config.submit()

        # config server
        server_iface = network.nodes[4]["interface"][0]["id"]
        server_config = network.open_node_config(4)
        server_config.fill_link("192.168.10.2", 24)
        server_config.fill_default_gw("192.168.10.3")
        server_config.add_jobs(
            203,
            {
                Location.Network.ConfigPanel.Server.Job.DHCP_IP_RANGE_START_FIELD.selector: "172.16.10.10",
                Location.Network.ConfigPanel.Server.Job.DHCP_IP_RANGE_END_FIELD.selector: "172.16.10.100",
                Location.Network.ConfigPanel.Server.Job.DHCP_MASK_FIELD.selector: "24",
                Location.Network.ConfigPanel.Server.Job.DHCP_IP_GW_FIELD.selector: "172.16.10.3",
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
                    "connect": "edge_mo0ldvxj74nu3vhlaio",
                    "id": "iface_16773533",
                    "name": "iface_16773533",
                }
            ],
            "position": {"x": 25, "y": 100},
        },
        {
            "classes": ["l2_switch"],
            "config": {"label": "l2sw1", "stp": 0, "type": "l2_switch"},
            "data": {"id": "l2sw1", "label": "l2sw1"},
            "interface": [
                {
                    "connect": "edge_mo0ldvxj74nu3vhlaio",
                    "id": "l2sw1_1",
                    "name": "l2sw1_1",
                    "type_connection": None,
                    "vlan": None,
                },
                {
                    "connect": "edge_mo0ldxdrueu0023e09",
                    "id": "l2sw1_2",
                    "name": "l2sw1_2",
                    "type_connection": None,
                    "vlan": None,
                },
            ],
            "position": {"x": 25, "y": 50},
        },
        {
            "classes": ["l3_router"],
            "config": {"default_gw": "", "label": "router_1", "type": "router"},
            "data": {"id": "router_1", "label": "router_1"},
            "interface": [
                {
                    "connect": "edge_mo0ldxdrueu0023e09",
                    "id": "iface_40424245",
                    "ip": "172.16.10.3",
                    "name": "iface_40424245",
                    "netmask": 24
                },
                {
                    "connect": "edge_mo0ldyffpg9scxw32yq",
                    "id": "iface_77344228",
                    "ip": "192.168.10.3",
                    "name": "iface_77344228",
                    "netmask": 24,
                },
            ],
            "position": {"x": 75, "y": 0},
        },
        {
            "classes": ["l2_switch"],
            "config": {"label": "l2sw2", "stp": 0, "type": "l2_switch"},
            "data": {"id": "l2sw2", "label": "l2sw2"},
            "interface": [
                {
                    "connect": "edge_mo0ldyffpg9scxw32yq",
                    "id": "l2sw2_1",
                    "name": "l2sw2_1",
                    "type_connection": None,
                    "vlan": None,
                },
                {
                    "connect": "edge_mo0ldzsfp1nakly2jf",
                    "id": "l2sw2_2",
                    "name": "l2sw2_2",
                    "type_connection": None,
                    "vlan": None,
                },
            ],
            "position": {"x": 100, "y": 50},
        },
        {
            "classes": ["server"],
            "config": {
                "default_gw": "192.168.10.3",
                "label": "server_1",
                "type": "server",
            },
            "data": {"id": "server_1", "label": "server_1"},
            "interface": [
                {
                    "connect": "edge_mo0ldzsfp1nakly2jf",
                    "id": "iface_28835140",
                    "ip": "192.168.10.2",
                    "name": "iface_28835140",
                    "netmask": 24,
                }
            ],
            "position": {"x": 100, "y": 100},
        },
    ]
    JSON_EDGES = [
        {
            "data": {
                "id": "edge_mo0ldvxj74nu3vhlaio",
                "source": "host_1",
                "target": "l2sw1",
                "loss_percentage": 0,
                "duplicate_percentage": 0,
            }
        },
        {
            "data": {
                "id": "edge_mo0ldxdrueu0023e09",
                "source": "l2sw1",
                "target": "router_1",
                "loss_percentage": 0,
                "duplicate_percentage": 0,
            }
        },
        {
            "data": {
                "id": "edge_mo0ldyffpg9scxw32yq",
                "source": "router_1",
                "target": "l2sw2",
                "loss_percentage": 0,
                "duplicate_percentage": 0,
            }
        },
        {
            "data": {
                "id": "edge_mo0ldzsfp1nakly2jf",
                "source": "l2sw2",
                "target": "server_1",
                "loss_percentage": 0,
                "duplicate_percentage": 0,
            }
        },
    ]
    JSON_JOBS = [
        {
            "id": "e8611d72c979483b940ddc5d2acebe6d",
            "job_id": 108,
            "print_cmd": "dhcp client",
            "arg_1": "iface_16773533",
            "level": 0,
            "host_id": "host_1",
        },
        {
            "id": "317a8189832c4477a8c34f916c9d8dbe",
            "job_id": 204,
            "print_cmd": "dnsmasq --dhcp-relay=172.16.10.3,192.168.10.2",
            "arg_1": "192.168.10.2",
            "arg_2": "172.16.10.3",
            "level": 1,
            "host_id": "router_1",
        },
        {
            "id": "437af3d8726a4363940552c89c201693",
            "job_id": 203,
            "print_cmd": "dhcp ip range: 172.16.10.10,172.16.10.100/24 gw: 172.16.10.3",
            "arg_1": "172.16.10.10",
            "arg_2": "172.16.10.100",
            "arg_3": "24",
            "arg_4": "172.16.10.3",
            "arg_5": "iface_28835140",
            "level": 2,
            "host_id": "server_1",
        },
    ]
