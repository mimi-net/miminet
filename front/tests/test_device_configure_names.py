import pytest
from conftest import MiminetTester
from utils.networks import MiminetTestNetwork, NodeType


class TestDeviceNameChange:
    @pytest.fixture(scope="class")
    def network(self, selenium: MiminetTester):
        network = MiminetTestNetwork(selenium)

        network.add_node(NodeType.Host)
        network.add_node(NodeType.Hub)
        network.add_node(NodeType.Router)
        network.add_node(NodeType.Server)
        network.add_node(NodeType.Switch)

        yield network

        network.delete()

    def test_device_name_change(
        self,
        selenium: MiminetTester,
        network: MiminetTestNetwork,
    ):
        """Just change the name of the device"""
        selenium.get(network.url)

        for node_id, node in enumerate(network.nodes):
            config = network.open_node_config(node)

            # change device name
            new_device_name = "new name!"
            config.change_name(new_device_name)

            # save data
            config.submit()

            updated_node = network.nodes[node_id]

            assert (
                updated_node["config"]["label"] == new_device_name
            ), "Failed to change device name."

    def test_device_name_change_to_long(
        self, selenium: MiminetTester, network: MiminetTestNetwork
    ):
        """Change device name to long string and checks if it has been cut"""
        for node_id, node in enumerate(network.nodes):
            config = network.open_node_config(node)

            # change device name
            new_device_name = "a" * 100  # long name
            config.change_name(new_device_name)

            # save changes
            config.submit()

            updated_node = network.nodes[node_id]

            # check that the name was cut off
            assert (
                updated_node["config"]["label"] != new_device_name
            ), "The device name isn't limited in size."
