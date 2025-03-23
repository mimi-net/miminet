import pytest
from conftest import MiminetTester
from utils.networks import MiminetTestNetwork, NodeType
import random


class TestDeviceConnecting:
    EDGES_COUNT = 10

    @pytest.fixture(scope="class")
    def network(self, selenium: MiminetTester):
        """Network with devices scattered across it."""
        network = MiminetTestNetwork(selenium)

        network.add_node(NodeType.Host)
        network.add_node(NodeType.Hub)
        network.add_node(NodeType.Router)
        network.add_node(NodeType.Server)
        network.add_node(NodeType.Switch)

        edges: set = set()

        while len(edges) < self.EDGES_COUNT:
            # random source and target for every edge
            source_node = random.randint(0, len(network.nodes) - 1)
            target_node = random.randint(0, len(network.nodes) - 1)

            if (source_node, target_node) not in edges:
                edges.add((source_node, target_node))
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

        # (label updates dynamically)
        from_label = selenium.execute_script("return $('#edge_source').val()")
        to_label = selenium.execute_script("return $('#edge_target').val()")

        # compare source and target
        assert (
            edge["data"]["source"] == from_label and edge["data"]["target"] == to_label
        ), f"Can't find path from {from_label} to {to_label} in edges"
