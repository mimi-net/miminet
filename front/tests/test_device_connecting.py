import pytest
from conftest import MiminetTester
from env.networks import MiminetTestNetwork
import random


class TestDeviceConnecting:
    EDGES_COUNT = 10

    @pytest.fixture(scope="class")
    def network(self, selenium: MiminetTester):
        network = MiminetTestNetwork(selenium)
        network.scatter_devices()

        for _ in range(self.EDGES_COUNT):
            source_node = random.choice(network.nodes)
            target_node = random.choice(network.nodes)

            network.add_edge(source_node, target_node)

        yield network

        network.delete()

    @pytest.mark.parametrize(
        "edge_id",
        (range(EDGES_COUNT)),
    )
    def test_edges_existence(
        self, selenium: MiminetTester, network: MiminetTestNetwork, edge_id: int
    ):
        edge = network.edges[edge_id]
        network.open_edge_config(edge)

        # label updates dynamically
        from_label = selenium.execute_script("return $('#edge_source').val()")
        to_label = selenium.execute_script("return $('#edge_target').val()")

        assert (
            edge["data"]["source"] == from_label and edge["data"]["target"] == to_label
        ), f"Can't find path from {from_label} to {to_label} in edges"