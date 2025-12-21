from typing import Tuple

import pytest

from front.tests.conftest import MiminetTester
from front.tests.utils.checkers import TestNetworkComparator
from front.tests.utils.networks import MiminetTestNetwork, NodeType
from utils.locators import Location


class TestPortForwardingTCP:

    @pytest.fixture(scope="class", params=["tcp", "udp"])
    def protocol_and_network(self, selenium: MiminetTester, request):
        protocol = request.param
        network = MiminetTestNetwork(selenium)
        network.add_node(NodeType.Host, 25, 50)
        network.add_node(NodeType.Router, 50, 25)
        network.add_node(NodeType.Server, 50, 50)

        network.add_edge(0, 1)
        network.add_edge(1, 2)

        host_config = network.open_node_config(0)
        host_config.fill_link("77.0.0.1", 30)
        host_config.fill_default_gw("77.0.0.2")
        host_config.submit()

        router_config = network.open_node_config(1)
        router_config.fill_link("77.0.0.2", 30, link_id=0)
        router_config.fill_link("10.0.0.2", 30, link_id=1)
        iface_id = network.nodes[1]["interface"][0]["id"]

        if protocol == "tcp":
            router_config.add_jobs(109, {
                Location.Network.ConfigPanel.Router.Job.PORT_FORWARDING_TCP_LINK_SELECT.selector: iface_id,
                Location.Network.ConfigPanel.Router.Job.PORT_FORWARDING_TCP_PORT_FIELD.selector: "80",
                Location.Network.ConfigPanel.Router.Job.PORT_FORWARDING_TCP_DEST_IP_FIELD.selector: "10.0.0.1",
                Location.Network.ConfigPanel.Router.Job.PORT_FORWARDING_TCP_DEST_PORT_FIELD.selector: "8000"}
                                   )
        elif protocol == "udp":
            router_config.add_jobs(110, {
                Location.Network.ConfigPanel.Router.Job.PORT_FORWARDING_UDP_LINK_SELECT.selector: iface_id,
                Location.Network.ConfigPanel.Router.Job.PORT_FORWARDING_UDP_PORT_FIELD.selector: "80",
                Location.Network.ConfigPanel.Router.Job.PORT_FORWARDING_UDP_DEST_IP_FIELD.selector: "10.0.0.1",
                Location.Network.ConfigPanel.Router.Job.PORT_FORWARDING_UDP_DEST_PORT_FIELD.selector: "8000"}
                                   )
        router_config.submit()

        server_config = network.open_node_config(2)
        server_config.fill_link("10.0.0.1", 30)
        server_config.submit()

        yield (protocol, network)

    def test_port_forwarding(self, selenium: MiminetTester, protocol_and_network: Tuple[str, MiminetTestNetwork]):
        protocol = protocol_and_network[0]
        network = protocol_and_network[1]
        assert TestNetworkComparator.compare_nodes(network.nodes, self.JSON_NODES)
        assert TestNetworkComparator.compare_edges(network.edges, self.JSON_EDGES)
        if protocol == "tcp":
            assert TestNetworkComparator.compare_jobs(network.jobs, self.JSON_TCP_JOBS)
        elif protocol == "udp":
            assert TestNetworkComparator.compare_jobs(network.jobs, self.JSON_UDP_JOBS)

    JSON_NODES = [
        {
            "classes": [
                "host"
            ],
            "config": {
                "default_gw": "77.0.0.2",
                "label": "host_1",
                "type": "host"
            },
            "data": {
                "id": "host_1",
                "label": "host_1"
            },
            "interface": [
                {
                    "connect": "edge_mjewlu699fb9rlmwpqa",
                    "id": "iface_34414560",
                    "ip": "77.0.0.1",
                    "name": "iface_34414560",
                    "netmask": 30
                }
            ],
            "position": {
                "x": 239.75,
                "y": 224.09375
            }
        },
        {
            "classes": [
                "l3_router"
            ],
            "config": {
                "default_gw": "",
                "label": "router_1",
                "type": "router"
            },
            "data": {
                "id": "router_1",
                "label": "router_1"
            },
            "interface": [
                {
                    "connect": "edge_mjewlu699fb9rlmwpqa",
                    "id": "iface_63630075",
                    "ip": "77.0.0.2",
                    "name": "iface_63630075",
                    "netmask": 30
                },
                {
                    "connect": "edge_mjewludcu7hg7klkmnh",
                    "id": "iface_45325888",
                    "ip": "10.0.0.2",
                    "name": "iface_45325888",
                    "netmask": 30
                }
            ],
            "position": {
                "x": 479.75,
                "y": 106.1875
            }
        },
        {
            "classes": [
                "server"
            ],
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
                    "connect": "edge_mjewludcu7hg7klkmnh",
                    "id": "iface_67026608",
                    "ip": "10.0.0.1",
                    "name": "iface_67026608",
                    "netmask": 30
                }
            ],
            "position": {
                "x": 479.75,
                "y": 223.484375
            }
        }
    ]
    JSON_EDGES = [
        {
            "data": {
                "id": "edge_mjewlu699fb9rlmwpqa",
                "source": "host_1",
                "target": "router_1"
            }
        },
        {
            "data": {
                "id": "edge_mjewludcu7hg7klkmnh",
                "source": "router_1",
                "target": "server_1"
            }
        }
    ]
    JSON_TCP_JOBS = [
        {
            "arg_1": "iface_63630075",
            "arg_2": "80",
            "arg_3": "10.0.0.1",
            "arg_4": "8000",
            "host_id": "router_1",
            "id": "d2ad1e858d74427e8848e07267a7e784",
            "job_id": 109,
            "level": 0,
            "print_cmd": "port forwarding -p tcp -i iface_63630075 from 80 to 10.0.0.1:8000"
        }
    ]
    JSON_UDP_JOBS = [
        {
            "arg_1": "iface_28208318",
            "arg_2": "80",
            "arg_3": "10.0.0.1",
            "arg_4": "8000",
            "host_id": "router_1",
            "id": "2d17acb877d94117b01d41a404016078",
            "job_id": 110,
            "level": 0,
            "print_cmd": "port forwarding -p udp -i iface_28208318 from 80 to 10.0.0.1:8000"
        }
    ]
