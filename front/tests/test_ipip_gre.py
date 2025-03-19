import pytest
from conftest import MiminetTester
from env.networks import (
    NodeType,
    MiminetTestNetwork,
)
from env.checkers import TestNetworkComparator
from env.locators import Location
from typing import Tuple


class TestIPIPGre:
    @pytest.fixture(scope="class", params=["ipip", "gre"])
    def protocol_and_network(self, selenium: MiminetTester, request):
        protocol = request.param
        network = MiminetTestNetwork(selenium)

        network.add_node(NodeType.Host, 25, 90)  # left host
        network.add_node(NodeType.Host, 75, 90)  # right host
        network.add_node(NodeType.Router, 25, 60)  # left router
        network.add_node(NodeType.Router, 75, 60)  # right router
        network.add_node(NodeType.Router, 50, 30)  # main router

        network.add_edge(0, 2)  # left host -> left router
        network.add_edge(1, 3)  # right host -> right router
        network.add_edge(2, 4)  # left router -> main router
        network.add_edge(3, 4)  # right router -> main router

        # configure hosts
        left_host_config = network.open_node_config(0)
        left_host_config.fill_link("192.168.1.2", 24)
        left_host_config.fill_default_gw("192.168.1.1")
        left_host_config.add_jobs(
            1, {Location.Network.ConfigPanel.Host.Job.PING_FIELD.selector: "10.0.0.2"}
        )
        left_host_config.submit()

        right_host_config = network.open_node_config(1)
        right_host_config.fill_link("10.0.0.2", 24)
        right_host_config.fill_default_gw("10.0.0.1")
        right_host_config.submit()

        # configure main router
        server_config = network.open_node_config(4)
        server_config.fill_link("212.220.12.2", 30, link_id=0)
        server_config.fill_link("212.220.12.6", 30, link_id=1)
        server_config.submit()

        # configure routers

        # - left
        left_router = network.open_node_config(2)
        left_router.fill_link("192.168.1.1", 24)
        left_router.fill_link("212.220.12.1", 30, link_id=1)
        left_router.fill_default_gw("212.220.12.2")
        left_router.submit()  # extra submit because job should select iface below

        left_iface_ip = network.nodes[2]["interface"][1]["ip"]

        if protocol == "ipip":
            left_router.add_jobs(
                105,
                {
                    Location.Network.ConfigPanel.Router.Job.IPIP_END_IP_FIELD.selector: "212.220.12.5",
                    Location.Network.ConfigPanel.Router.Job.IPIP_IFACE_IP_FIELD.selector: "1.1.1.1",
                    Location.Network.ConfigPanel.Router.Job.IPIP_NAME_IFACE_FIELD.selector: "tun1",
                    Location.Network.ConfigPanel.Router.Job.IPIP_IFACE_SELECT.selector: left_iface_ip,
                },
            )
        elif protocol == "gre":
            left_router.add_jobs(
                106,
                {
                    Location.Network.ConfigPanel.Router.Job.GRE_END_IP_FIELD.selector: "212.220.12.5",
                    Location.Network.ConfigPanel.Router.Job.GRE_IFACE_IP_FIELD.selector: "1.1.1.1",
                    Location.Network.ConfigPanel.Router.Job.GRE_NAME_IFACE_FIELD.selector: "gre1",
                    Location.Network.ConfigPanel.Router.Job.GRE_IFACE_SELECT.selector: left_iface_ip,
                },
            )
        else:
            raise ValueError(f"Unsupported protocol: {protocol}.")

        left_router.submit()

        left_router.add_jobs(
            102,
            {
                Location.Network.ConfigPanel.Router.Job.ADD_ROUTE_IP_FIELD.selector: "10.0.0.0",
                Location.Network.ConfigPanel.Router.Job.ADD_ROUTE_MASK_FIELD.selector: "24",
                Location.Network.ConfigPanel.Router.Job.ADD_ROUTE_IP_GW_FIELD.selector: "1.1.1.1",
            },
        )

        left_router.submit()

        # - right

        right_router = network.open_node_config(3)
        right_router.fill_link("10.0.0.1", 24)
        right_router.fill_link("212.220.12.5", 30, link_id=1)
        right_router.fill_default_gw("212.220.12.6")
        right_router.submit()

        right_iface_ip = network.nodes[3]["interface"][1]["ip"]

        if protocol == "ipip":
            right_router.add_jobs(
                105,
                {
                    Location.Network.ConfigPanel.Router.Job.IPIP_END_IP_FIELD.selector: "212.220.12.1",
                    Location.Network.ConfigPanel.Router.Job.IPIP_IFACE_IP_FIELD.selector: "2.2.2.2",
                    Location.Network.ConfigPanel.Router.Job.IPIP_NAME_IFACE_FIELD.selector: "tun1",
                    Location.Network.ConfigPanel.Router.Job.IPIP_IFACE_SELECT.selector: right_iface_ip,
                },
            )
        elif protocol == "gre":
            right_router.add_jobs(
                106,
                {
                    Location.Network.ConfigPanel.Router.Job.GRE_END_IP_FIELD.selector: "212.220.12.1",
                    Location.Network.ConfigPanel.Router.Job.GRE_IFACE_IP_FIELD.selector: "2.2.2.2",
                    Location.Network.ConfigPanel.Router.Job.GRE_NAME_IFACE_FIELD.selector: "gre1",
                    Location.Network.ConfigPanel.Router.Job.GRE_IFACE_SELECT.selector: right_iface_ip,
                },
            )
        else:
            raise ValueError(f"Unsupported protocol: {protocol}.")

        right_router.submit()

        right_router.add_jobs(
            102,
            {
                Location.Network.ConfigPanel.Router.Job.ADD_ROUTE_IP_FIELD.selector: "192.168.1.0",
                Location.Network.ConfigPanel.Router.Job.ADD_ROUTE_MASK_FIELD.selector: "24",
                Location.Network.ConfigPanel.Router.Job.ADD_ROUTE_IP_GW_FIELD.selector: "2.2.2.2",
            },
        )

        right_router.submit()

        # end configure

        yield (protocol, network)

        # network.delete()

    def test_ipip_gre(
        self,
        selenium: MiminetTester,
        protocol_and_network: Tuple[str, MiminetTestNetwork],
    ):
        protocol: str = protocol_and_network[0]
        network: MiminetTestNetwork = protocol_and_network[1]

        assert TestNetworkComparator.compare_nodes(self.JSON_NODES, network.nodes)
        assert TestNetworkComparator.compare_edges(self.JSON_EDGES, network.edges)

        if protocol == "ipip":
            assert TestNetworkComparator.compare_jobs(self.JSON_IPIP_JOBS, network.jobs)
        elif protocol == "gre":
            assert TestNetworkComparator.compare_jobs(self.JSON_GRE_JOBS, network.jobs)
        else:
            raise ValueError(f"Got unsupported protocol: {protocol}.")

    JSON_NODES = [
        {
            "data": {"id": "host_1", "label": "host_1"},
            "position": {"x": 108.5, "y": 342},
            "classes": ["host"],
            "config": {"type": "host", "label": "host_1", "default_gw": "192.168.1.1"},
            "interface": [
                {
                    "id": "iface_30236432",
                    "name": "iface_30236432",
                    "connect": "edge_m4lgu9gsjbme17i8zif",
                    "ip": "192.168.1.2",
                    "netmask": 24,
                }
            ],
        },
        {
            "data": {"id": "host_2", "label": "host_2"},
            "position": {"x": 326.5, "y": 342},
            "classes": ["host"],
            "config": {"type": "host", "label": "host_2", "default_gw": "10.0.0.1"},
            "interface": [
                {
                    "id": "iface_34100558",
                    "name": "iface_34100558",
                    "connect": "edge_m4lgu9n3n17xaty4bci",
                    "ip": "10.0.0.2",
                    "netmask": 24,
                }
            ],
        },
        {
            "data": {"id": "router_1", "label": "router_1"},
            "position": {"x": 108.5, "y": 224.296875},
            "classes": ["l3_router"],
            "config": {
                "type": "router",
                "label": "router_1",
                "default_gw": "212.220.12.2",
            },
            "interface": [
                {
                    "id": "iface_88301271",
                    "name": "iface_88301271",
                    "connect": "edge_m4lgu9gsjbme17i8zif",
                    "ip": "192.168.1.1",
                    "netmask": 24,
                },
                {
                    "id": "iface_87710016",
                    "name": "iface_87710016",
                    "connect": "edge_m4lgu9u8ez3e6x650yv",
                    "ip": "212.220.12.1",
                    "netmask": 30,
                },
            ],
        },
        {
            "data": {"id": "router_2", "label": "router_2"},
            "position": {"x": 326.5, "y": 224.296875},
            "classes": ["l3_router"],
            "config": {
                "type": "router",
                "label": "router_2",
                "default_gw": "212.220.12.6",
            },
            "interface": [
                {
                    "id": "iface_78483308",
                    "name": "iface_78483308",
                    "connect": "edge_m4lgu9n3n17xaty4bci",
                    "ip": "10.0.0.1",
                    "netmask": 24,
                },
                {
                    "id": "iface_18686083",
                    "name": "iface_18686083",
                    "connect": "edge_m4lgua096okairi8dvv",
                    "ip": "212.220.12.5",
                    "netmask": 30,
                },
            ],
        },
        {
            "data": {"id": "router_3", "label": "router_3"},
            "position": {"x": 217.5, "y": 106.796875},
            "classes": ["l3_router"],
            "config": {"type": "router", "label": "router_3", "default_gw": ""},
            "interface": [
                {
                    "id": "iface_64827022",
                    "name": "iface_64827022",
                    "connect": "edge_m4lgu9u8ez3e6x650yv",
                    "ip": "212.220.12.2",
                    "netmask": 30,
                },
                {
                    "id": "iface_83816582",
                    "name": "iface_83816582",
                    "connect": "edge_m4lgua096okairi8dvv",
                    "ip": "212.220.12.6",
                    "netmask": 30,
                },
            ],
        },
    ]
    JSON_EDGES = [
        {
            "data": {
                "id": "edge_m4lgu9gsjbme17i8zif",
                "source": "host_1",
                "target": "router_1",
            }
        },
        {
            "data": {
                "id": "edge_m4lgu9n3n17xaty4bci",
                "source": "host_2",
                "target": "router_2",
            }
        },
        {
            "data": {
                "id": "edge_m4lgu9u8ez3e6x650yv",
                "source": "router_1",
                "target": "router_3",
            }
        },
        {
            "data": {
                "id": "edge_m4lgua096okairi8dvv",
                "source": "router_2",
                "target": "router_3",
            }
        },
    ]
    JSON_IPIP_JOBS = [
        {
            "id": "1308aaefb7ef4793963081144f2e4bfe",
            "job_id": 1,
            "print_cmd": "ping -c 1 10.0.0.2",
            "arg_1": "10.0.0.2",
            "level": 0,
            "host_id": "host_1",
        },
        {
            "id": "0967b6e7a15e47b59371b1fcf071c2ae",
            "job_id": 105,
            "print_cmd": "ipip: tun1 from 212.220.12.1 to 212.220.12.5 \\ntun1: 1.1.1.1",
            "arg_1": "212.220.12.1",
            "arg_2": "212.220.12.5",
            "arg_3": "1.1.1.1",
            "arg_4": "tun1",
            "level": 1,
            "host_id": "router_1",
        },
        {
            "id": "ec0f6eb00e144af9b768289d180cf5b7",
            "job_id": 102,
            "print_cmd": "ip route add 10.0.0.0/24 via 1.1.1.1",
            "arg_1": "10.0.0.0",
            "arg_2": "24",
            "arg_3": "1.1.1.1",
            "level": 2,
            "host_id": "router_1",
        },
        {
            "id": "8ceabccc72f64e518839496ea5dcade5",
            "job_id": 105,
            "print_cmd": "ipip: tun1 from 212.220.12.5 to 212.220.12.1 \\ntun1: 2.2.2.2",
            "arg_1": "212.220.12.5",
            "arg_2": "212.220.12.1",
            "arg_3": "2.2.2.2",
            "arg_4": "tun1",
            "level": 3,
            "host_id": "router_2",
        },
        {
            "id": "1ff30c6540e04ad1a9a971054b43907a",
            "job_id": 102,
            "print_cmd": "ip route add 192.168.1.0/24 via 2.2.2.2",
            "arg_1": "192.168.1.0",
            "arg_2": "24",
            "arg_3": "2.2.2.2",
            "level": 4,
            "host_id": "router_2",
        },
    ]
    JSON_GRE_JOBS = [
        {
            "id": "3d772afdb92346e494ec4ce2be06670c",
            "job_id": 1,
            "print_cmd": "ping -c 1 10.0.0.2",
            "arg_1": "10.0.0.2",
            "level": 0,
            "host_id": "host_1",
        },
        {
            "id": "5c6500d702fe40ec81f97ecbac01da96",
            "job_id": 106,
            "print_cmd": "gre: gre1 from 212.220.12.1 to 212.220.12.5 \\ngre1: 1.1.1.1",
            "arg_1": "212.220.12.1",
            "arg_2": "212.220.12.5",
            "arg_3": "1.1.1.1",
            "arg_4": "gre1",
            "level": 1,
            "host_id": "router_1",
        },
        {
            "id": "4d6b4edc071442dfa0039e04994834c2",
            "job_id": 102,
            "print_cmd": "ip route add 10.0.0.0/24 via 1.1.1.1",
            "arg_1": "10.0.0.0",
            "arg_2": "24",
            "arg_3": "1.1.1.1",
            "level": 2,
            "host_id": "router_1",
        },
        {
            "id": "3ddd5aced20e449398d865f60b77db8b",
            "job_id": 106,
            "print_cmd": "gre: gre1 from 212.220.12.5 to 212.220.12.1 \\ngre1: 2.2.2.2",
            "arg_1": "212.220.12.5",
            "arg_2": "212.220.12.1",
            "arg_3": "2.2.2.2",
            "arg_4": "gre1",
            "level": 3,
            "host_id": "router_2",
        },
        {
            "id": "0ea61c5290164b6890a3c246d35a9b44",
            "job_id": 102,
            "print_cmd": "ip route add 192.168.1.0/24 via 2.2.2.2",
            "arg_1": "192.168.1.0",
            "arg_2": "24",
            "arg_3": "2.2.2.2",
            "level": 4,
            "host_id": "router_2",
        },
    ]
