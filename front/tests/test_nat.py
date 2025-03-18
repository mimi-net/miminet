import pytest
from conftest import MiminetTester
from env.networks import (
    NodeConfig,
    NodeType,
    MiminetTestNetwork,
    compare_jobs,
    compare_nodes,
    compare_edges,
)
from env.locators import Location


class TestNat:

    @pytest.fixture(scope="class")
    def network(self, selenium: MiminetTester):
        network = MiminetTestNetwork(selenium)

        # nodes
        network.add_node(NodeType.Host, 25, 30)  # top host
        network.add_node(NodeType.Host, 25, 70)  # bottom host
        network.add_node(NodeType.Router, 50, 30)  # top router
        network.add_node(NodeType.Router, 50, 70)  # bottom router
        network.add_node(NodeType.Router, 70, 50)  # center router
        network.add_node(NodeType.Server, 90, 50)  # server

        # edges
        network.add_edge(0, 2)  # top host -> top router
        network.add_edge(1, 3)  # bottom host -> bottom router
        network.add_edge(2, 4)  # top router -> center router
        network.add_edge(3, 4)  # bottom router -> center router
        network.add_edge(4, 5)  # center router -> server

        # configure hosts
        # - top host
        top_host_config = network.open_node_config(0)
        self.configure_client_host(top_host_config)

        # - bottom host
        bottom_host_config = network.open_node_config(1)
        self.configure_client_host(bottom_host_config)

        # configure routers
        # - top router
        top_router_config = network.open_node_config(2)
        self.configure_client_router(
            top_router_config,
            "172.16.0.1",
            "172.16.0.2",
            network.nodes[2]["interface"][1]["id"],
        )

        # - bottom router
        bottom_router_config = network.open_node_config(3)
        self.configure_client_router(
            bottom_router_config,
            "172.16.1.1",
            "172.16.1.2",
            network.nodes[3]["interface"][1]["id"],
        )

        # configure center router
        center_router_config = network.open_node_config(4)
        center_router_config.fill_link("172.16.0.2", 24, 0)
        center_router_config.fill_link("172.16.1.2", 24, 1)
        center_router_config.fill_link("10.0.0.2", 24, 2)

        center_router_config.submit()

        # configure server
        server_config = network.open_node_config(5)
        server_config.fill_link("10.0.0.1", 24)
        server_config.fill_default_gw("10.0.0.2")
        server_config.submit()

        yield network

        network.delete()

    def configure_client_host(self, config: NodeConfig):
        config.fill_link("192.168.1.1", 24)
        config.fill_default_gw("192.168.1.2")
        config.add_jobs(
            1,
            {Location.Network.ConfigPanel.Host.Job.PING_FIELD.selector: "10.0.0.1"},
        )
        config.submit()

    def configure_client_router(
        self, config: NodeConfig, out_ip: str, out_gw: str, iface_id: str
    ):
        config.fill_link("192.168.1.2", 24, link_id=0)
        config.fill_link(out_ip, 24, link_id=1)
        config.fill_default_gw(out_gw)
        config.add_jobs(
            101,
            {
                Location.Network.ConfigPanel.Router.Job.NAT_LINK_SELECT.selector: iface_id
            },
        )

        config.submit()

    def test_nat(self, selenium: MiminetTester, network: MiminetTestNetwork):
        assert compare_nodes(network.nodes, self.JSON_NODES)
        assert compare_edges(network.edges, self.JSON_EDGES)
        assert compare_jobs(network.jobs, self.JSON_JOBS)

    JSON_NODES = [
        {
            "data": {"id": "host_1", "label": "host_1"},
            "position": {"x": 108.5, "y": 100},
            "classes": ["host"],
            "config": {"type": "host", "label": "host_1", "default_gw": "192.168.1.2"},
            "interface": [
                {
                    "id": "iface_25851384",
                    "name": "iface_25851384",
                    "connect": "edge_m4fnjzsfnvyba8evla",
                    "ip": "192.168.1.1",
                    "netmask": 24,
                }
            ],
        },
        {
            "data": {"id": "host_2", "label": "host_2"},
            "position": {"x": 108.5, "y": 249},
            "classes": ["host"],
            "config": {"type": "host", "label": "host_2", "default_gw": "192.168.1.2"},
            "interface": [
                {
                    "id": "iface_54681060",
                    "name": "iface_54681060",
                    "connect": "edge_m4fnjzxqayf33zskw5",
                    "ip": "192.168.1.1",
                    "netmask": 24,
                }
            ],
        },
        {
            "data": {"id": "router_1", "label": "router_1"},
            "position": {"x": 217.5, "y": 100.296875},
            "classes": ["l3_router"],
            "config": {
                "type": "router",
                "label": "router_1",
                "default_gw": "172.16.0.2",
            },
            "interface": [
                {
                    "id": "iface_80482202",
                    "name": "iface_80482202",
                    "connect": "edge_m4fnjzsfnvyba8evla",
                    "ip": "192.168.1.2",
                    "netmask": 24,
                },
                {
                    "id": "iface_12758605",
                    "name": "iface_12758605",
                    "connect": "edge_m4fnk02nf6jq3vrysvm",
                    "ip": "172.16.0.1",
                    "netmask": 24,
                },
            ],
        },
        {
            "data": {"id": "router_2", "label": "router_2"},
            "position": {"x": 217.5, "y": 249.296875},
            "classes": ["l3_router"],
            "config": {
                "type": "router",
                "label": "router_2",
                "default_gw": "172.16.1.2",
            },
            "interface": [
                {
                    "id": "iface_84681556",
                    "name": "iface_84681556",
                    "connect": "edge_m4fnjzxqayf33zskw5",
                    "ip": "192.168.1.2",
                    "netmask": 24,
                },
                {
                    "id": "iface_45687608",
                    "name": "iface_45687608",
                    "connect": "edge_m4fnk07lm7eij89kg2k",
                    "ip": "172.16.1.1",
                    "netmask": 24,
                },
            ],
        },
        {
            "data": {"id": "router_3", "label": "router_3"},
            "position": {"x": 304.5, "y": 174.796875},
            "classes": ["l3_router"],
            "config": {"type": "router", "label": "router_3", "default_gw": ""},
            "interface": [
                {
                    "id": "iface_57725535",
                    "name": "iface_57725535",
                    "connect": "edge_m4fnk02nf6jq3vrysvm",
                    "ip": "172.16.0.2",
                    "netmask": 24,
                },
                {
                    "id": "iface_32265235",
                    "name": "iface_32265235",
                    "connect": "edge_m4fnk07lm7eij89kg2k",
                    "ip": "172.16.1.2",
                    "netmask": 24,
                },
                {
                    "id": "iface_62103865",
                    "name": "iface_62103865",
                    "connect": "edge_m4fnk0cyh2eomgicpvg",
                    "ip": "10.0.0.2",
                    "netmask": 24,
                },
            ],
        },
        {
            "data": {"id": "server_1", "label": "server_1"},
            "position": {"x": 391.5, "y": 174.59375},
            "classes": ["server"],
            "config": {"type": "server", "label": "server_1", "default_gw": "10.0.0.2"},
            "interface": [
                {
                    "id": "iface_43508723",
                    "name": "iface_43508723",
                    "connect": "edge_m4fnk0cyh2eomgicpvg",
                    "ip": "10.0.0.1",
                    "netmask": 24,
                }
            ],
        },
    ]
    JSON_EDGES = [
        {
            "data": {
                "id": "edge_m4fnjzsfnvyba8evla",
                "source": "host_1",
                "target": "router_1",
            }
        },
        {
            "data": {
                "id": "edge_m4fnjzxqayf33zskw5",
                "source": "host_2",
                "target": "router_2",
            }
        },
        {
            "data": {
                "id": "edge_m4fnk02nf6jq3vrysvm",
                "source": "router_1",
                "target": "router_3",
            }
        },
        {
            "data": {
                "id": "edge_m4fnk07lm7eij89kg2k",
                "source": "router_2",
                "target": "router_3",
            }
        },
        {
            "data": {
                "id": "edge_m4fnk0cyh2eomgicpvg",
                "source": "router_3",
                "target": "server_1",
            }
        },
    ]
    JSON_JOBS = [
        {
            "id": "9f857db567824291b1c0d5eeca337fcc",
            "job_id": 1,
            "print_cmd": "ping -c 1 10.0.0.1",
            "arg_1": "10.0.0.1",
            "level": 0,
            "host_id": "host_1",
        },
        {
            "id": "bc0acd02e6e641dcb658be0ea1cfdc0a",
            "job_id": 1,
            "print_cmd": "ping -c 1 10.0.0.1",
            "arg_1": "10.0.0.1",
            "level": 1,
            "host_id": "host_2",
        },
        {
            "id": "dd4a7eb7af8d419aa599df6683f65369",
            "job_id": 101,
            "print_cmd": "add nat -o iface_12758605 -j masquerad",
            "arg_1": "iface_12758605",
            "level": 2,
            "host_id": "router_1",
        },
        {
            "id": "5b9592a274fe46839983dd81753c4731",
            "job_id": 101,
            "print_cmd": "add nat -o iface_45687608 -j masquerad",
            "arg_1": "iface_45687608",
            "level": 3,
            "host_id": "router_2",
        },
    ]
