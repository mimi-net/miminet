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
        network.add_node(NodeType.Host, 250, 275)  # host
        network.add_node(NodeType.Switch, 250, 175)  # switch 1
        network.add_node(NodeType.Router, 350, 75) # router
        network.add_node(NodeType.Switch, 400, 175)  # switch 2
        network.add_node(NodeType.Server, 400, 275)  # server

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
            "classes": ["l2_switch"],
            "config": {
                "label": "l2sw1",
                "stp": 0,
                "type": "l2_switch"
            },
            "data": {
                "id": "l2sw1",
                "label": "l2sw1"
            },
            "interface": [
                {
                    "connect": "edge_mnxf20jpi9lk28vbr2",
                    "id": "l2sw1_1",
                    "name": "l2sw1_1",
                    "type_connection": None,
                    "vlan": None
                },
                {
                    "connect": "edge_mnym51eah6wx0v6s9h",
                    "id": "l2sw1_2",
                    "name": "l2sw1_2",
                    "type_connection": None,
                    "vlan": None
                }
            ],
            "position": {
                "x": 25,
                "y": 50
            }
        },
        {
            "classes": ["l2_switch"],
            "config": {
                "label": "l2sw2",
                "stp": 0,
                "type": "l2_switch"
            },
            "data": {
                "id": "l2sw2",
                "label": "l2sw2"
            },
            "interface": [
                {
                    "connect": "edge_mnwcvw5j8b38v1xr5sj",
                    "id": "l2sw2_2",
                    "name": "l2sw2_2",
                    "type_connection": None,
                    "vlan": None
                },
                {
                    "connect": "edge_mnym5331cjpgqzraqy4",
                    "id": "l2sw2_3",
                    "name": "l2sw2_3",
                    "type_connection": None,
                    "vlan": None
                }
            ],
            "position": {
                "x": 100,
                "y": 50
            }
        },
        {
            "classes": ["server"],
            "config": {
                "default_gw": "",
                "label": "server_1",
                "type": "server"
            },
            "data": {
                "id": "server_1",
                "label": "server_1"
            },
            "interface": [
                {
                    "connect": "edge_mnwcvw5j8b38v1xr5sj",
                    "id": "iface_16417632",
                    "ip": "192.168.10.2",
                    "name": "iface_16417632",
                    "netmask": 24
                }
            ],
            "position": {
                "x": 100,
                "y": 100
            }
        },
        {
            "classes": ["host"],
            "config": {
                "default_gw": "",
                "label": "host_1",
                "type": "host"
            },
            "data": {
                "id": "host_1",
                "label": "host_1"
            },
            "interface": [
                {
                    "connect": "edge_mnxf20jpi9lk28vbr2",
                    "id": "iface_46653148",
                    "name": "iface_46653148"
                }
            ],
            "position": {
                "x": 25,
                "y": 100
            }
        },
        {
            "classes": ["l3_router"],
            "config": {
                "default_gw": "",
                "label": "router_1",
                "type": "router"
            },
            "data": {
                "id": "router_2",
                "label": "router_1"
            },
            "interface": [
                {
                    "connect": "edge_mnym51eah6wx0v6s9h",
                    "id": "iface_02514152",
                    "ip": "172.16.10.3",
                    "name": "iface_02514152",
                    "netmask": 24
                },
                {
                    "connect": "edge_mnym5331cjpgqzraqy4",
                    "id": "iface_64411470",
                    "ip": "192.168.10.3",
                    "name": "iface_64411470",
                    "netmask": 24
                }
            ],
            "position": {
                "x": 75,
                "y": 0
            }
        }
    ]
    JSON_EDGES = [
        {
            "data": {
                "id": "edge_mnysboa63sl7masz29i",
                "source": "host_1",
                "target": "l2sw1",
                "loss_percentage": 0,
                "duplicate_percentage": 0
            }
        },
        {
            "data": {
                "id": "edge_mnysbpcfq1uwnl5unw",
                "source": "l2sw1",
                "target": "router_1",
                "loss_percentage": 0,
                "duplicate_percentage": 0
            }
        },
        {
            "data": {
                "id": "edge_mnysbqjka0cbjig1jb7",
                "source": "router_1",
                "target": "l2sw2",
                "loss_percentage": 0,
                "duplicate_percentage": 0
            }
        },
        {
            "data": {
                "id": "edge_mnysbrok5nl01pdvoe3",
                "source": "l2sw2",
                "target": "server_1",
                "loss_percentage": 0,
                "duplicate_percentage": 0
            }
        }
    ]
    JSON_JOBS = [
        {
            "id": "90f1af9818c24105b9418c1a503eb04d",
            "job_id": 108,
            "print_cmd": "dhcp client",
            "arg_1": "iface_61426530",
            "level": 0,
            "host_id": "host_1"
        },
        {
            "id": "60b97a16a1cd4ae2aaa921b77f7ec2fd",
            "job_id": 204,
            "print_cmd": "dnsmasq --dhcp-relay=172.16.10.3,192.168.10.2",
            "arg_1": "192.168.10.2",
            "arg_2": "172.16.10.3",
            "level": 1,
            "host_id": "router_1"
        },
        {
            "id": "1ed7256caf6f4f75ae50eddb5607920c",
            "job_id": 203,
            "print_cmd": "dhcp ip range: 172.16.10.10,172.16.10.100/24 gw: 172.16.10.3",
            "arg_1": "172.16.10.10",
            "arg_2": "172.16.10.100",
            "arg_3": "24",
            "arg_4": "172.16.10.3",
            "arg_5": "iface_84271537",
            "level": 2,
            "host_id": "server_1"
        }
    ]
