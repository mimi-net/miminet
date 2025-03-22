import pytest
from conftest import MiminetTester
from utils.networks import NodeConfig, NodeType, MiminetTestNetwork
from utils.locators import Location


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
        selenium.save_screenshot('2.png')
        # l2sw1_config.submit()
        selenium.refresh()
        network.open_node_config(l2sw1_id)
        selenium.save_screenshot('3.png')

        # configure right switch
        # l2sw2_config = network.open_node_config(l2sw2_id)
        # selenium.save_screenshot('3.png')
        # l2sw2_config.configure_vlan(
        #     {
        #         "l2sw1": ("10,20", "Trunk"),
        #         "host_2": ("10", "Access"),
        #         "host_4": ("20", "Access"),
        #     },
        # )
        # l2sw2_config.submit()

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
        print(network.url)
        assert False
