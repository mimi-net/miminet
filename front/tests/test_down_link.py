import pytest
from conftest import MiminetTester
from utils.networks import NodeType, MiminetTestNetwork
from utils.locators import Location
from utils.checkers import TestNetworkComparator


class TestLinkDown:

    @pytest.fixture(scope="class")
    def network(self, selenium: MiminetTester):
        network = MiminetTestNetwork(selenium)

        # nodes
        network.add_node(NodeType.Host, 25, 80)  # host 1
        network.add_node(NodeType.Host, 100, 80)  # host 2
        network.add_node(NodeType.Switch, 50, 80)  # switch 1

        network.add_edge(0, 2)
        network.add_edge(2, 1)
        switch1_config = network.open_node_config(2)
        correct_iface = network.nodes[2]["interface"][1]["id"]
        switch1_config.add_jobs(
            6,
            {
                Location.Network.ConfigPanel.Switch.Job.LINK_DOWN_OPTION_FIELD.selector: correct_iface
            },
        )
        switch1_config.submit()

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

    def test_link_down(self, selenium: MiminetTester, network: MiminetTestNetwork):
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
                    "connect": "edge_mj9bwjdpddmbw7jy57g",
                    "id": "iface_02341508",
                    "ip": "192.168.0.1",
                    "name": "iface_02341508",
                    "netmask": 24,
                }
            ],
            "position": {"x": 114.75, "y": 159.0999984741211},
        },
        {
            "classes": ["host"],
            "config": {"default_gw": "", "label": "host_2", "type": "host"},
            "data": {"id": "host_2", "label": "host_2"},
            "interface": [
                {
                    "connect": "edge_mj9bwkfzr4g5rsyn5ri",
                    "id": "iface_35385083",
                    "ip": "192.168.0.2",
                    "name": "iface_35385083",
                    "netmask": 24,
                }
            ],
            "position": {"x": 211.75, "y": 160.0999984741211},
        },
        {
            "classes": ["l2_switch"],
            "config": {"label": "l2sw1", "stp": 0, "type": "l2_switch"},
            "data": {"id": "l2sw1", "label": "l2sw1"},
            "interface": [
                {
                    "connect": "edge_mj9bwjdpddmbw7jy57g",
                    "id": "l2sw1_1",
                    "name": "l2sw1_1",
                    "type_connection": None,
                    "vlan": None,
                },
                {
                    "connect": "edge_mj9bwkfzr4g5rsyn5ri",
                    "id": "l2sw1_2",
                    "name": "l2sw1_2",
                    "type_connection": None,
                    "vlan": None,
                },
            ],
            "position": {"x": 162.25, "y": 155.3000030517578},
        },
    ]

    JSON_JOBS = [
        {
            "arg_1": "l2sw1_2",
            "arg_2": "host_2",
            "host_id": "l2sw1",
            "id": "94f7fef66da1496383ba58efdbf91384",
            "job_id": 6,
            "level": 1,
            "print_cmd": "link down host_2",
        },
        {
            "arg_1": "192.168.0.2",
            "host_id": "host_1",
            "id": "8070c3bd8668497ba39c56ebc80d91f1",
            "job_id": 1,
            "level": 0,
            "print_cmd": "ping -c 1 192.168.0.2",
        },
    ]
    JSON_EDGES = [
        {
            "data": {
                "id": "edge_mj9bwjdpddmbw7jy57g",
                "loss_percentage": 0,
                "source": "host_1",
                "target": "l2sw1",
            }
        },
        {
            "data": {
                "id": "edge_mj9bwkfzr4g5rsyn5ri",
                "loss_percentage": 0,
                "source": "l2sw1",
                "target": "host_2",
            }
        },
    ]
