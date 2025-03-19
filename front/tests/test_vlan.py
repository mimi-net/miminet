import pytest
from conftest import MiminetTester
from env.networks import NodeConfig, NodeType, MiminetTestNetwork
from env.checkers import TestNetworkComparator
from env.locators import Location


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

        # config hosts
        host1_id = network.open_node_config(host1_id)
        self.configure_left_host(host1_id)
        host2_id = network.open_node_config(host2_id)
        self.configure_right_host(host2_id)
        host3_id = network.open_node_config(host3_id)
        self.configure_left_host(host3_id)
        host4_id = network.open_node_config(host4_id)
        self.configure_right_host(host4_id)

        selenium.save_screenshot('3.png')

        # # configure hosts
        # # - top host
        # top_host_config = network.open_node_config(0)
        # self.configure_client_host(top_host_config)

        # # - bottom host
        # bottom_host_config = network.open_node_config(1)
        # self.configure_client_host(bottom_host_config)

        # # configure routers
        # # - top router
        # top_router_config = network.open_node_config(2)
        # self.configure_client_router(
        #     top_router_config,
        #     "172.16.0.1",
        #     "172.16.0.2",
        #     network.nodes[2]["interface"][1]["id"],
        # )

        # # - bottom router
        # bottom_router_config = network.open_node_config(3)
        # self.configure_client_router(
        #     bottom_router_config,
        #     "172.16.1.1",
        #     "172.16.1.2",
        #     network.nodes[3]["interface"][1]["id"],
        # )

        # # configure center router
        # center_router_config = network.open_node_config(4)
        # center_router_config.fill_link("172.16.0.2", 24, 0)
        # center_router_config.fill_link("172.16.1.2", 24, 1)
        # center_router_config.fill_link("10.0.0.2", 24, 2)

        # center_router_config.submit()

        # # configure server
        # server_config = network.open_node_config(5)
        # server_config.fill_link("10.0.0.1", 24)
        # server_config.fill_default_gw("10.0.0.2")
        # server_config.submit()

        yield network

        # network.delete()

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

    def configure_client_router(
        self, config: NodeConfig, out_ip: str, out_gw: str, iface_id: str
    ):
        # TODO
        pass

    def test_vlan(self, selenium: MiminetTester, network: MiminetTestNetwork):
        print(network.url)

        assert TestNetworkComparator.compare_nodes(network.nodes, self.JSON_NODES)
        assert TestNetworkComparator.compare_edges(network.edges, self.JSON_EDGES)
        assert TestNetworkComparator.compare_jobs(network.jobs, self.JSON_JOBS)

    JSON_NODES = []
    JSON_EDGES = []
    JSON_JOBS = []
