import pytest
from conftest import MiminetTester
from utils.networks import NodeType, MiminetTestNetwork
from utils.locators import Location
from utils.checkers import TestNetworkComparator


class TestSTP:

    @pytest.fixture(scope="class")
    def network(self, selenium: MiminetTester):
        network = MiminetTestNetwork(selenium)

        # nodes
        network.add_node(NodeType.Host, 25, 80)  # host 1
        network.add_node(NodeType.Host, 75, 80)  # host 2
        network.add_node(NodeType.Switch, 50, 65)  # switch 1
        network.add_node(NodeType.Switch, 25, 55)  # switch 2
        network.add_node(NodeType.Switch, 75, 55)  # switch 3

        # edges
        network.add_edge(0, 2)  # host 1 -> switch 1
        network.add_edge(1, 2)  # host 2 -> switch 1
        network.add_edge(3, 2)  # switch 2 -> switch 1
        network.add_edge(3, 4)  # switch 2 -> switch 3
        network.add_edge(4, 2)  # switch 3 -> switch 1

        # configure hosts
        host1_config = network.open_node_config(0)
        host1_config.fill_link("192.168.1.1", 24)
        host1_config.add_jobs(
            1,
            {Location.Network.ConfigPanel.Host.Job.PING_FIELD.selector: "192.168.1.2"},
        )
        host1_config.submit()

        host2_config = network.open_node_config(1)
        host2_config.fill_link("192.168.1.2", 24)
        host2_config.submit()

        # config switches
        switch1_config = network.open_node_config(2)
        switch1_config.enable_stp()  # ON stp
        switch1_config.disable_stp()  # OFF stp (just for test)
        switch1_config.submit()
        selenium.refresh()

        switch2_config = network.open_node_config(3)
        switch2_config.enable_stp()  # ON stp
        switch2_config.submit()
        selenium.refresh()

        switch3_config = network.open_node_config(4)
        switch3_config.enable_stp()  # ON stp
        switch3_config.disable_stp()  # OFF stp (just for test)
        switch3_config.submit()

        yield network

        network.delete()

    def test_stp(self, selenium: MiminetTester, network: MiminetTestNetwork):
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
                    "connect": "edge_m8fhge6mq6efxjuudpc",
                    "id": "iface_82668626",
                    "ip": "192.168.1.1",
                    "name": "iface_82668626",
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
                    "connect": "edge_m8fhgecytmhfm3vejz",
                    "id": "iface_42526255",
                    "ip": "192.168.1.2",
                    "name": "iface_42526255",
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
                    "connect": "edge_m8fhge6mq6efxjuudpc",
                    "id": "l2sw1_1",
                    "name": "l2sw1_1",
                    "type_connection": None,
                    "vlan": None,
                },
                {
                    "connect": "edge_m8fhgecytmhfm3vejz",
                    "id": "l2sw1_2",
                    "name": "l2sw1_2",
                    "type_connection": None,
                    "vlan": None,
                },
                {
                    "connect": "edge_m8fhgeiy4hw8zlk4ln",
                    "id": "l2sw1_3",
                    "name": "l2sw1_3",
                    "type_connection": None,
                    "vlan": None,
                },
                {
                    "connect": "edge_m8fhgewkc7sjvovx51j",
                    "id": "l2sw1_4",
                    "name": "l2sw1_4",
                    "type_connection": None,
                    "vlan": None,
                },
            ],
            "position": {"x": 217.5, "y": 243.5},
        },
        {
            "classes": ["l2_switch"],
            "config": {"label": "l2sw2", "stp": 1, "type": "l2_switch"},
            "data": {"id": "l2sw2", "label": "l2sw2"},
            "interface": [
                {
                    "connect": "edge_m8fhgeiy4hw8zlk4ln",
                    "id": "l2sw2_1",
                    "name": "l2sw2_1",
                    "type_connection": None,
                    "vlan": None,
                },
                {
                    "connect": "edge_m8fhgepyc015jxj6abk",
                    "id": "l2sw2_2",
                    "name": "l2sw2_2",
                    "type_connection": None,
                    "vlan": None,
                },
            ],
            "position": {"x": 108.5, "y": 204.5},
        },
        {
            "classes": ["l2_switch"],
            "config": {"label": "l2sw3", "stp": 0, "type": "l2_switch"},
            "data": {"id": "l2sw3", "label": "l2sw3"},
            "interface": [
                {
                    "connect": "edge_m8fhgepyc015jxj6abk",
                    "id": "l2sw3_1",
                    "name": "l2sw3_1",
                    "type_connection": None,
                    "vlan": None,
                },
                {
                    "connect": "edge_m8fhgewkc7sjvovx51j",
                    "id": "l2sw3_2",
                    "name": "l2sw3_2",
                    "type_connection": None,
                    "vlan": None,
                },
            ],
            "position": {"x": 326.5, "y": 204.5},
        },
    ]

    JSON_EDGES = [
        {
            "data": {
                "id": "edge_m8fhge6mq6efxjuudpc",
                "source": "host_1",
                "target": "l2sw1",
            }
        },
        {
            "data": {
                "id": "edge_m8fhgecytmhfm3vejz",
                "source": "host_2",
                "target": "l2sw1",
            }
        },
        {
            "data": {
                "id": "edge_m8fhgeiy4hw8zlk4ln",
                "source": "l2sw2",
                "target": "l2sw1",
            }
        },
        {
            "data": {
                "id": "edge_m8fhgepyc015jxj6abk",
                "source": "l2sw2",
                "target": "l2sw3",
            }
        },
        {
            "data": {
                "id": "edge_m8fhgewkc7sjvovx51j",
                "source": "l2sw3",
                "target": "l2sw1",
            }
        },
    ]
    JSON_JOBS = [
        {
            "arg_1": "192.168.1.2",
            "host_id": "host_1",
            "id": "cd3f2ff8a6a045ba8c345f29e9fc4c17",
            "job_id": 1,
            "level": 0,
            "print_cmd": "ping -c 1 192.168.1.2",
        }
    ]
