import pytest
from conftest import MiminetTester
from utils.networks import NodeConfig, NodeType, MiminetTestNetwork
from utils.locators import Location
from utils.checkers import TestNetworkComparator


class TestVLAN:

    @pytest.fixture(scope="class")
    def network(self, selenium: MiminetTester):
        network = MiminetTestNetwork(selenium)

        # nodes
        host1_id = network.add_node(NodeType.Host, 25, 25)
        host2_id = network.add_node(NodeType.Host, 75, 25)
        host3_id = network.add_node(NodeType.Host, 25, 50)
        host4_id = network.add_node(NodeType.Host, 75, 50)
        l2sw1_id = network.add_node(NodeType.Switch, 40, 35.5)
        l2sw2_id = network.add_node(NodeType.Switch, 60, 35.5)

        # edges
        network.add_edge(host1_id, l2sw1_id)
        network.add_edge(host2_id, l2sw2_id)
        network.add_edge(host3_id, l2sw1_id)
        network.add_edge(host4_id, l2sw2_id)

        network.add_edge(l2sw1_id, l2sw2_id)

        # configure hosts
        host1_config = network.open_node_config(host1_id)
        self.configure_left_host(host1_config)
        host2_config = network.open_node_config(host2_id)
        self.configure_right_host(host2_config)
        host3_config = network.open_node_config(host3_id)
        self.configure_left_host(host3_config)
        host4_config = network.open_node_config(host4_id)
        self.configure_right_host(host4_config)

        # configure left switch
        l2sw1_config = network.open_node_config(l2sw1_id)
        l2sw1_config.configure_vlan(
            {
                "l2sw2": ("10,20", "Trunk"),
                "host_1": ("10", "Access"),
                "host_3": ("20", "Access"),
            },
        )
        l2sw1_config.submit()

        # selenium (or VLAN code) doesn't allow re-interaction with vlan form without refreshing
        selenium.refresh()

        # configure right switch
        l2sw2_config = network.open_node_config(l2sw2_id)
        l2sw2_config.configure_vlan(
            {
                "l2sw1": ("10,20", "Trunk"),
                "host_2": ("10", "Access"),
                "host_4": ("20", "Access"),
            },
        )
        l2sw2_config.submit()

        yield network

        network.delete()

    def configure_left_host(self, config: NodeConfig):
        config.fill_link("10.0.0.1", 24)
        config.add_jobs(
            1,
            {Location.Network.ConfigPanel.Host.Job.PING_FIELD.selector: "10.0.0.2"},
        )
        config.submit()

    def configure_right_host(self, config: NodeConfig):
        config.fill_link("10.0.0.2", 24)
        config.submit()

    def test_vlan(self, selenium: MiminetTester, network: MiminetTestNetwork):
        assert TestNetworkComparator.compare_nodes(self.JSON_NODES, network.nodes)
        assert TestNetworkComparator.compare_edges(self.JSON_EDGES, network.edges)
        assert TestNetworkComparator.compare_jobs(self.JSON_JOBS, network.jobs)

    JSON_NODES = [
        {
            "classes": ["host"],
            "config": {"default_gw": "", "label": "host_1", "type": "host"},
            "data": {"id": "host_1", "label": "host_1"},
            "interface": [
                {
                    "connect": "edge_m8llhem5fmccigh4ne",
                    "id": "iface_06074200",
                    "ip": "10.0.0.1",
                    "name": "iface_06074200",
                    "netmask": 24,
                }
            ],
            "position": {"x": 108.5, "y": 81.5},
        },
        {
            "classes": ["host"],
            "config": {"default_gw": "", "label": "host_2", "type": "host"},
            "data": {"id": "host_2", "label": "host_2"},
            "interface": [
                {
                    "connect": "edge_m8llhevc0plhwsiuw0s",
                    "id": "iface_65487112",
                    "ip": "10.0.0.2",
                    "name": "iface_65487112",
                    "netmask": 24,
                }
            ],
            "position": {"x": 326.5, "y": 81.5},
        },
        {
            "classes": ["host"],
            "config": {"default_gw": "", "label": "host_3", "type": "host"},
            "data": {"id": "host_3", "label": "host_3"},
            "interface": [
                {
                    "connect": "edge_m8llhf7481nr9ar52fh",
                    "id": "iface_85870513",
                    "ip": "10.0.0.1",
                    "name": "iface_85870513",
                    "netmask": 24,
                }
            ],
            "position": {"x": 108.5, "y": 174.5},
        },
        {
            "classes": ["host"],
            "config": {"default_gw": "", "label": "host_4", "type": "host"},
            "data": {"id": "host_4", "label": "host_4"},
            "interface": [
                {
                    "connect": "edge_m8llhffak9jd26o49dl",
                    "id": "iface_11682264",
                    "ip": "10.0.0.2",
                    "name": "iface_11682264",
                    "netmask": 24,
                }
            ],
            "position": {"x": 326.5, "y": 174.5},
        },
        {
            "classes": ["l2_switch"],
            "config": {"label": "l2sw1", "stp": 0, "type": "l2_switch"},
            "data": {"id": "l2sw1", "label": "l2sw1"},
            "interface": [
                {
                    "connect": "edge_m8llhem5fmccigh4ne",
                    "id": "l2sw1_1",
                    "name": "l2sw1_1",
                    "type_connection": 0,
                    "vlan": 10,
                },
                {
                    "connect": "edge_m8llhf7481nr9ar52fh",
                    "id": "l2sw1_2",
                    "name": "l2sw1_2",
                    "type_connection": 0,
                    "vlan": 20,
                },
                {
                    "connect": "edge_m8llhfmu0rqjach341i9",
                    "id": "l2sw1_3",
                    "name": "l2sw1_3",
                    "type_connection": 1,
                    "vlan": [10, 20],
                },
            ],
            "position": {"x": 174, "y": 120.5},
        },
        {
            "classes": ["l2_switch"],
            "config": {"label": "l2sw2", "stp": 0, "type": "l2_switch"},
            "data": {"id": "l2sw2", "label": "l2sw2"},
            "interface": [
                {
                    "connect": "edge_m8llhevc0plhwsiuw0s",
                    "id": "l2sw2_1",
                    "name": "l2sw2_1",
                    "type_connection": 0,
                    "vlan": 10,
                },
                {
                    "connect": "edge_m8llhffak9jd26o49dl",
                    "id": "l2sw2_2",
                    "name": "l2sw2_2",
                    "type_connection": 0,
                    "vlan": 20,
                },
                {
                    "connect": "edge_m8llhfmu0rqjach341i9",
                    "id": "l2sw2_3",
                    "name": "l2sw2_3",
                    "type_connection": 1,
                    "vlan": [10, 20],
                },
            ],
            "position": {"x": 261, "y": 120.5},
        },
    ]
    JSON_EDGES = [
        {
            "data": {
                "id": "edge_m8llhem5fmccigh4ne",
                "source": "host_1",
                "target": "l2sw1",
            }
        },
        {
            "data": {
                "id": "edge_m8llhevc0plhwsiuw0s",
                "source": "host_2",
                "target": "l2sw2",
            }
        },
        {
            "data": {
                "id": "edge_m8llhf7481nr9ar52fh",
                "source": "host_3",
                "target": "l2sw1",
            }
        },
        {
            "data": {
                "id": "edge_m8llhffak9jd26o49dl",
                "source": "host_4",
                "target": "l2sw2",
            }
        },
        {
            "data": {
                "id": "edge_m8llhfmu0rqjach341i9",
                "source": "l2sw1",
                "target": "l2sw2",
            }
        },
    ]
    JSON_JOBS = [
        {
            "id": "c56093e3187e402e964018a5ec8f5403",
            "job_id": 1,
            "print_cmd": "ping -c 1 10.0.0.2",
            "arg_1": "10.0.0.2",
            "level": 0,
            "host_id": "host_1",
        },
        {
            "id": "c3b6ef62d6be47f2af4338ce88d516da",
            "job_id": 1,
            "print_cmd": "ping -c 1 10.0.0.2",
            "arg_1": "10.0.0.2",
            "level": 1,
            "host_id": "host_3",
        },
    ]
