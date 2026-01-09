import pytest
from conftest import MiminetTester
from utils.networks import NodeType, MiminetTestNetwork
from utils.locators import Location
from utils.checkers import TestNetworkComparator


class TestSleepJob:

    @pytest.fixture(scope="class")
    def network(self, selenium: MiminetTester):
        network = MiminetTestNetwork(selenium)

        # nodes
        network.add_node(NodeType.Host, 25, 80)  # host 1
        network.add_node(NodeType.Host, 100, 80)  # host 2
        network.add_node(NodeType.Switch, 70, 80)  # switch 1
        network.add_node(NodeType.Switch, 60, 80)  # switch 2

        network.add_edge(0, 2)
        network.add_edge(2, 3)
        network.add_edge(3, 1)
        switch1_config = network.open_node_config(2)
        switch1_config.add_jobs(
            7,
            {Location.Network.ConfigPanel.Switch.Job.SLEEP_FIELD.selector: 1},
        )
        switch1_config.submit()

        switch2_config = network.open_node_config(3)
        switch2_config.add_jobs(
            7,
            {Location.Network.ConfigPanel.Switch.Job.SLEEP_FIELD.selector: 2},
        )
        switch2_config.submit()

        host1_config = network.open_node_config(0)
        host1_config.fill_link("192.168.0.1", 24)
        host1_config.add_jobs(
            1,
            {Location.Network.ConfigPanel.Host.Job.PING_FIELD.selector: "192.168.0.2"},
        )
        host1_config.submit()
        host2_config = network.open_node_config(1)
        host2_config.fill_link("192.168.0.2", 24)
        host2_config.submit()
        yield network

        network.delete()

    def test_sleep(self, selenium: MiminetTester, network: MiminetTestNetwork):
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
                    "connect": "edge_mja6jjc8mmvzla27e9b",
                    "id": "iface_64614221",
                    "ip": "192.168.0.1",
                    "name": "iface_64614221",
                    "netmask": 24,
                }
            ],
            "position": {"x": 116.75, "y": 166.0999984741211},
        },
        {
            "classes": ["host"],
            "config": {"default_gw": "", "label": "host_2", "type": "host"},
            "data": {"id": "host_2", "label": "host_2"},
            "interface": [
                {
                    "connect": "edge_mja6jlcta05x47iidy4",
                    "id": "iface_35122260",
                    "ip": "192.168.0.2",
                    "name": "iface_35122260",
                    "netmask": 24,
                }
            ],
            "position": {"x": 270.75, "y": 160.0999984741211},
        },
        {
            "classes": ["l2_switch"],
            "config": {"label": "l2sw1", "stp": 0, "type": "l2_switch"},
            "data": {"id": "l2sw1", "label": "l2sw1"},
            "interface": [
                {
                    "connect": "edge_mja6jjc8mmvzla27e9b",
                    "id": "l2sw1_1",
                    "name": "l2sw1_1",
                    "type_connection": None,
                    "vlan": None,
                },
                {
                    "connect": "edge_mja6jkel2a60m7lsxyp",
                    "id": "l2sw1_2",
                    "name": "l2sw1_2",
                    "type_connection": None,
                    "vlan": None,
                },
            ],
            "position": {"x": 186.75, "y": 168.3000030517578},
        },
        {
            "classes": ["l2_switch"],
            "config": {"label": "l2sw2", "stp": 0, "type": "l2_switch"},
            "data": {"id": "l2sw2", "label": "l2sw2"},
            "interface": [
                {
                    "connect": "edge_mja6jkel2a60m7lsxyp",
                    "id": "l2sw2_1",
                    "name": "l2sw2_1",
                    "type_connection": None,
                    "vlan": None,
                },
                {
                    "connect": "edge_mja6jlcta05x47iidy4",
                    "id": "l2sw2_2",
                    "name": "l2sw2_2",
                    "type_connection": None,
                    "vlan": None,
                },
            ],
            "position": {"x": 229.75, "y": 164.8000030517578},
        },
    ]
    JSON_JOBS = [
        {
            "arg_1": "3",
            "host_id": "l2sw1",
            "id": "a926948427f04e108590ea6424d61ffc",
            "job_id": 7,
            "level": 0,
            "print_cmd": "sleep 1 seconds",
        },
        {
            "arg_1": "4",
            "host_id": "l2sw2",
            "id": "1aebc209668240ffbbc5e3f70a55a0e7",
            "job_id": 7,
            "level": 1,
            "print_cmd": "sleep 2 seconds",
        },
        {
            "arg_1": "192.168.0.2",
            "host_id": "host_1",
            "id": "ee0c3314be1f4892ae39e1e2e9bc45b3",
            "job_id": 1,
            "level": 2,
            "print_cmd": "ping -c 1 192.168.0.2",
        },
    ]
    JSON_EDGES = [
        {
            "data": {
                "duplicate_percentage": 0,
                "id": "edge_mja6jjc8mmvzla27e9b",
                "loss_percentage": 0,
                "source": "host_1",
                "target": "l2sw1",
            }
        },
        {
            "data": {
                "duplicate_percentage": 0,
                "id": "edge_mja6jkel2a60m7lsxyp",
                "loss_percentage": 0,
                "source": "l2sw1",
                "target": "l2sw2",
            }
        },
        {
            "data": {
                "duplicate_percentage": 0,
                "id": "edge_mja6jlcta05x47iidy4",
                "loss_percentage": 0,
                "source": "l2sw2",
                "target": "host_2",
            }
        },
    ]
