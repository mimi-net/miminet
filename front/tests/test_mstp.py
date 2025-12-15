import pytest
from tests.utils.miminet_tester import MiminetTester
from tests.utils.networks import MiminetTestNetwork
from tests.utils.comparator import TestNetworkComparator


class TestMSTP:
    @pytest.fixture(scope="class")
    def network(self, selenium: MiminetTester):
        network = MiminetTestNetwork(selenium)

        # Add hosts
        network.add_host(1, 1, "host1")
        network.add_host(1, 3, "host2")
        network.add_host(3, 3, "host3")

        # Add switches
        network.add_l2_switch(2, 1, "l2sw1")
        network.add_l2_switch(2, 2, "l2sw2")
        network.add_l2_switch(2, 3, "l2sw3")

        # Add links
        network.add_link("host1", "l2sw1")
        network.add_link("l2sw1", "l2sw2")
        network.add_link("l2sw2", "l2sw3")
        network.add_link("l2sw3", "host3")
        network.add_link("host2", "l2sw2")
        network.add_link("l2sw1", "l2sw3")  # Create loop for STP

        network.submit()

        # config switches
        switch1_config = network.open_node_config(2)
        switch1_config.enable_mstp()  # ON mstp
        switch1_config.submit()
        selenium.refresh()

        switch2_config = network.open_node_config(3)
        switch2_config.enable_mstp()  # ON mstp
        switch2_config.submit()
        selenium.refresh()

        switch3_config = network.open_node_config(4)
        switch3_config.enable_mstp()  # ON mstp
        switch3_config.submit()

        yield network

        network.delete()

    def test_mstp(self, selenium: MiminetTester, network: MiminetTestNetwork):
        assert TestNetworkComparator.compare_nodes(network.nodes, self.JSON_NODES)
        assert TestNetworkComparator.compare_edges(network.edges, self.JSON_EDGES)

    JSON_NODES = [
        {
            "classes": ["host"],
            "config": {"label": "host1", "type": "host"},
            "data": {"id": "host1", "label": "host1"},
            "interface": [
                {
                    "connect": "l2sw1",
                    "id": "host1_1",
                    "ip": "",
                    "name": "host1_1",
                    "netmask": 0,
                    "type_connection": None,
                    "vlan": None,
                    "vxlan_connection_type": None,
                    "vxlan_vni": None,
                    "vxlan_vni_to_target_ip": None,
                }
            ],
            "position": {"x": 1, "y": 1},
        },
        {
            "classes": ["l2_switch"],
            "config": {"label": "l2sw1", "stp": 3, "type": "l2_switch"},
            "data": {"id": "l2sw1", "label": "l2sw1"},
            "interface": [
                {
                    "connect": "host1",
                    "id": "l2sw1_1",
                    "ip": "",
                    "name": "l2sw1_1",
                    "netmask": 0,
                    "type_connection": None,
                    "vlan": None,
                    "vxlan_connection_type": None,
                    "vxlan_vni": None,
                    "vxlan_vni_to_target_ip": None,
                },
                {
                    "connect": "l2sw2",
                    "id": "l2sw1_2",
                    "ip": "",
                    "name": "l2sw1_2",
                    "netmask": 0,
                    "type_connection": None,
                    "vlan": None,
                    "vxlan_connection_type": None,
                    "vxlan_vni": None,
                    "vxlan_vni_to_target_ip": None,
                },
                {
                    "connect": "l2sw3",
                    "id": "l2sw1_3",
                    "ip": "",
                    "name": "l2sw1_3",
                    "netmask": 0,
                    "type_connection": None,
                    "vlan": None,
                    "vxlan_connection_type": None,
                    "vxlan_vni": None,
                    "vxlan_vni_to_target_ip": None,
                },
            ],
            "position": {"x": 2, "y": 1},
        },
        {
            "classes": ["l2_switch"],
            "config": {"label": "l2sw2", "stp": 3, "type": "l2_switch"},
            "data": {"id": "l2sw2", "label": "l2sw2"},
            "interface": [
                {
                    "connect": "l2sw1",
                    "id": "l2sw2_1",
                    "ip": "",
                    "name": "l2sw2_1",
                    "netmask": 0,
                    "type_connection": None,
                    "vlan": None,
                    "vxlan_connection_type": None,
                    "vxlan_vni": None,
                    "vxlan_vni_to_target_ip": None,
                },
                {
                    "connect": "l2sw3",
                    "id": "l2sw2_2",
                    "ip": "",
                    "name": "l2sw2_2",
                    "netmask": 0,
                    "type_connection": None,
                    "vlan": None,
                    "vxlan_connection_type": None,
                    "vxlan_vni": None,
                    "vxlan_vni_to_target_ip": None,
                },
                {
                    "connect": "host2",
                    "id": "l2sw2_3",
                    "ip": "",
                    "name": "l2sw2_3",
                    "netmask": 0,
                    "type_connection": None,
                    "vlan": None,
                    "vxlan_connection_type": None,
                    "vxlan_vni": None,
                    "vxlan_vni_to_target_ip": None,
                },
            ],
            "position": {"x": 2, "y": 2},
        },
        {
            "classes": ["l2_switch"],
            "config": {"label": "l2sw3", "stp": 3, "type": "l2_switch"},
            "data": {"id": "l2sw3", "label": "l2sw3"},
            "interface": [
                {
                    "connect": "l2sw2",
                    "id": "l2sw3_1",
                    "ip": "",
                    "name": "l2sw3_1",
                    "netmask": 0,
                    "type_connection": None,
                    "vlan": None,
                    "vxlan_connection_type": None,
                    "vxlan_vni": None,
                    "vxlan_vni_to_target_ip": None,
                },
                {
                    "connect": "host3",
                    "id": "l2sw3_2",
                    "ip": "",
                    "name": "l2sw3_2",
                    "netmask": 0,
                    "type_connection": None,
                    "vlan": None,
                    "vxlan_connection_type": None,
                    "vxlan_vni": None,
                    "vxlan_vni_to_target_ip": None,
                },
                {
                    "connect": "l2sw1",
                    "id": "l2sw3_3",
                    "ip": "",
                    "name": "l2sw3_3",
                    "netmask": 0,
                    "type_connection": None,
                    "vlan": None,
                    "vxlan_connection_type": None,
                    "vxlan_vni": None,
                    "vxlan_vni_to_target_ip": None,
                },
            ],
            "position": {"x": 2, "y": 3},
        },
        {
            "classes": ["host"],
            "config": {"label": "host2", "type": "host"},
            "data": {"id": "host2", "label": "host2"},
            "interface": [
                {
                    "connect": "l2sw2",
                    "id": "host2_1",
                    "ip": "",
                    "name": "host2_1",
                    "netmask": 0,
                    "type_connection": None,
                    "vlan": None,
                    "vxlan_connection_type": None,
                    "vxlan_vni": None,
                    "vxlan_vni_to_target_ip": None,
                }
            ],
            "position": {"x": 1, "y": 3},
        },
        {
            "classes": ["host"],
            "config": {"label": "host3", "type": "host"},
            "data": {"id": "host3", "label": "host3"},
            "interface": [
                {
                    "connect": "l2sw3",
                    "id": "host3_1",
                    "ip": "",
                    "name": "host3_1",
                    "netmask": 0,
                    "type_connection": None,
                    "vlan": None,
                    "vxlan_connection_type": None,
                    "vxlan_vni": None,
                    "vxlan_vni_to_target_ip": None,
                }
            ],
            "position": {"x": 3, "y": 3},
        },
    ]

    JSON_EDGES = [
        {"data": {"id": "host1_l2sw1", "source": "host1", "target": "l2sw1"}},
        {"data": {"id": "l2sw1_l2sw2", "source": "l2sw1", "target": "l2sw2"}},
        {"data": {"id": "l2sw2_l2sw3", "source": "l2sw2", "target": "l2sw3"}},
        {"data": {"id": "l2sw3_host3", "source": "l2sw3", "target": "host3"}},
        {"data": {"id": "host2_l2sw2", "source": "host2", "target": "l2sw2"}},
        {"data": {"id": "l2sw1_l2sw3", "source": "l2sw1", "target": "l2sw3"}},
    ]
