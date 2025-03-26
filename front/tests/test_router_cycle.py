import pytest
from conftest import MiminetTester
from utils.networks import NodeConfig, NodeType, MiminetTestNetwork
from utils.locators import Location
from utils.checkers import TestNetworkComparator


class TestRouterCycle:

    @pytest.fixture(scope="class")
    def network(self, selenium: MiminetTester):
        network = MiminetTestNetwork(selenium)

        # nodes
        network.add_node(NodeType.Host, 25, 50)  # single host
        network.add_node(NodeType.Router, 50, 25)  # router 1
        network.add_node(NodeType.Router, 90, 25)  # router 2
        network.add_node(NodeType.Router, 75, 50)  # router 3

        # edges
        network.add_edge(0, 1)  # host -> router 1
        network.add_edge(1, 2)  # router 1 -> router 2
        network.add_edge(2, 3)  # router 2 -> router 3
        network.add_edge(3, 1)  # router 3 -> router 1

        # host config
        host_config = network.open_node_config(0)
        self.configure_host(host_config)

        # routers config
        router1_config = network.open_node_config(1)
        self.configure_router(
            router1_config,
            ["10.0.0.2:23", "172.16.12.1:24", "169.254.1.1:24"],
            "172.16.12.2",
        )

        router2_config = network.open_node_config(2)
        self.configure_router(
            router2_config, ["172.16.12.2:24", "192.168.1.2:24"], "192.168.1.1"
        )

        router3_config = network.open_node_config(3)
        self.configure_router(
            router3_config, ["192.168.1.1:24", "169.254.1.2:24"], "169.254.1.1"
        )

        yield network

        network.delete()

    def configure_host(self, config: NodeConfig):
        config.fill_link("10.0.0.1", 24)
        config.fill_default_gw("10.0.0.2")
        config.add_jobs(
            1,
            {Location.Network.ConfigPanel.Host.Job.PING_FIELD.selector: "12.34.45.67"},
        )
        config.submit()

    def configure_router(self, config: NodeConfig, ip_mask_links: list[str], gw: str):
        config.fill_links(ip_mask_links)
        config.fill_default_gw(gw)
        config.submit()

    def test_cycle(self, selenium: MiminetTester, network: MiminetTestNetwork):
        assert TestNetworkComparator.compare_nodes(network.nodes, self.JSON_NODES)
        assert TestNetworkComparator.compare_jobs(network.jobs, self.JSON_JOBS)

    JSON_NODES = [
        {
            "classes": ["host"],
            "config": {"default_gw": "10.0.0.2", "label": "host_1", "type": "host"},
            "data": {"id": "host_1", "label": "host_1"},
            "interface": [
                {
                    "connect": "edge_m8epdumx4eroqjsqdcv",
                    "id": "iface_78046210",
                    "ip": "10.0.0.1",
                    "name": "iface_78046210",
                    "netmask": 24,
                }
            ],
            "position": {"x": 108.5, "y": 174.5},
        },
        {
            "classes": ["l3_router"],
            "config": {
                "default_gw": "172.16.12.2",
                "label": "router_1",
                "type": "router",
            },
            "data": {"id": "router_1", "label": "router_1"},
            "interface": [
                {
                    "connect": "edge_m8epdumx4eroqjsqdcv",
                    "id": "iface_76323745",
                    "ip": "10.0.0.2",
                    "name": "iface_76323745",
                    "netmask": 23,
                },
                {
                    "connect": "edge_m8epdusxi7qa1lr26o",
                    "id": "iface_88257846",
                    "ip": "172.16.12.1",
                    "name": "iface_88257846",
                    "netmask": 24,
                },
                {
                    "connect": "edge_m8epdv5lndvzmt3im5",
                    "id": "iface_41756500",
                    "ip": "169.254.1.1",
                    "name": "iface_41756500",
                    "netmask": 24,
                },
            ],
            "position": {"x": 217.5, "y": 81.796875},
        },
        {
            "classes": ["l3_router"],
            "config": {
                "default_gw": "192.168.1.1",
                "label": "router_2",
                "type": "router",
            },
            "data": {"id": "router_2", "label": "router_2"},
            "interface": [
                {
                    "connect": "edge_m8epdusxi7qa1lr26o",
                    "id": "iface_80000451",
                    "ip": "172.16.12.2",
                    "name": "iface_80000451",
                    "netmask": 24,
                },
                {
                    "connect": "edge_m8epduyxy36mmf3hndm",
                    "id": "iface_26866256",
                    "ip": "192.168.1.2",
                    "name": "iface_26866256",
                    "netmask": 24,
                },
            ],
            "position": {"x": 391.5, "y": 81.796875},
        },
        {
            "classes": ["l3_router"],
            "config": {
                "default_gw": "169.254.1.1",
                "label": "router_3",
                "type": "router",
            },
            "data": {"id": "router_3", "label": "router_3"},
            "interface": [
                {
                    "connect": "edge_m8epduyxy36mmf3hndm",
                    "id": "iface_87300542",
                    "ip": "192.168.1.1",
                    "name": "iface_87300542",
                    "netmask": 24,
                },
                {
                    "connect": "edge_m8epdv5lndvzmt3im5",
                    "id": "iface_32804550",
                    "ip": "169.254.1.2",
                    "name": "iface_32804550",
                    "netmask": 24,
                },
            ],
            "position": {"x": 326.5, "y": 174.796875},
        },
    ]
    JSON_JOBS = [
        {
            "arg_1": "12.34.45.67",
            "host_id": "host_1",
            "id": "8cd2382cb87441ce8f0f9504978d7a63",
            "job_id": 1,
            "level": 0,
            "print_cmd": "ping -c 1 12.34.45.67",
        }
    ]
