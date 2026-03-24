import time
import pytest
from conftest import MiminetTester
from utils.networks import NodeType, MiminetTestNetwork
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from utils.locators import Location


class TestCopyPaste:
    """Tests for multi-select, copy (Ctrl+C) and paste (Ctrl+V) of network elements."""

    @pytest.fixture(scope="class")
    def network(self, selenium: MiminetTester):
        network = MiminetTestNetwork(selenium)

        host1_id = network.add_node(NodeType.Host)
        host2_id = network.add_node(NodeType.Host)
        router_id = network.add_node(NodeType.Router)

        network.add_edge(host1_id, host2_id)
        network.add_edge(host2_id, router_id)

        # configure host 1
        config = network.open_node_config(host1_id)
        config.fill_link("10.0.0.1", 24)
        config.add_jobs(
            1,
            {Location.Network.ConfigPanel.Host.Job.PING_FIELD.selector: "10.0.0.2"},
        )
        config.submit()

        # configure host 2
        config = network.open_node_config(host2_id)
        config.fill_link("10.0.0.2", 24)
        config.submit()

        yield network

        network.delete()

    def _select_all(self, selenium: MiminetTester):
        """Select all elements via Ctrl+A."""
        canvas = selenium.find_element(By.ID, "network_scheme")
        canvas.click()
        time.sleep(0.3)
        ActionChains(selenium).key_down(Keys.CONTROL).send_keys("a").key_up(Keys.CONTROL).perform()
        time.sleep(0.3)

    def _copy(self, selenium: MiminetTester):
        """Copy selected elements via Ctrl+C."""
        ActionChains(selenium).key_down(Keys.CONTROL).send_keys("c").key_up(Keys.CONTROL).perform()
        time.sleep(0.3)

    def _paste(self, selenium: MiminetTester):
        """Paste from clipboard via Ctrl+V."""
        ActionChains(selenium).key_down(Keys.CONTROL).send_keys("v").key_up(Keys.CONTROL).perform()
        time.sleep(0.5)

    def _deselect_all(self, selenium: MiminetTester):
        """Deselect all via Escape."""
        ActionChains(selenium).send_keys(Keys.ESCAPE).perform()
        time.sleep(0.3)

    def _get_selected_count(self, selenium: MiminetTester):
        """Get number of selected elements in Cytoscape."""
        return selenium.execute_script("return global_cy.elements(':selected').length")

    def test_select_all(self, selenium: MiminetTester, network: MiminetTestNetwork):
        """Ctrl+A should select all nodes and edges."""
        selenium.get(network.url)
        time.sleep(1)

        self._select_all(selenium)

        total_nodes = len(network.nodes)
        total_edges = len(network.edges)
        selected = self._get_selected_count(selenium)

        assert selected == total_nodes + total_edges, (
            f"Expected {total_nodes + total_edges} selected, got {selected}"
        )

    def test_deselect_escape(self, selenium: MiminetTester, network: MiminetTestNetwork):
        """Escape should deselect all elements."""
        selenium.get(network.url)
        time.sleep(1)

        self._select_all(selenium)
        assert self._get_selected_count(selenium) > 0

        self._deselect_all(selenium)
        assert self._get_selected_count(selenium) == 0

    def test_copy_paste_duplicates_elements(
        self, selenium: MiminetTester, network: MiminetTestNetwork
    ):
        """Ctrl+C then Ctrl+V should duplicate selected nodes and edges."""
        selenium.get(network.url)
        time.sleep(1)

        nodes_before = len(network.nodes)
        edges_before = len(network.edges)

        # Select all, copy, paste
        self._select_all(selenium)
        self._copy(selenium)
        self._paste(selenium)
        time.sleep(0.5)

        nodes_after = len(network.nodes)
        edges_after = len(network.edges)

        assert nodes_after == nodes_before * 2, (
            f"Expected {nodes_before * 2} nodes after paste, got {nodes_after}"
        )
        assert edges_after == edges_before * 2, (
            f"Expected {edges_before * 2} edges after paste, got {edges_after}"
        )

    def test_pasted_nodes_have_unique_ids(
        self, selenium: MiminetTester
    ):
        """Pasted nodes should have new unique IDs (uses fresh network)."""
        net = MiminetTestNetwork(selenium)
        h1 = net.add_node(NodeType.Host)
        h2 = net.add_node(NodeType.Host)
        net.add_edge(h1, h2)
        time.sleep(0.5)

        original_count = len(net.nodes)

        self._select_all(selenium)
        self._copy(selenium)
        self._paste(selenium)
        time.sleep(0.5)

        all_ids = [n["data"]["id"] for n in net.nodes]

        # Total nodes should double
        assert len(all_ids) == original_count * 2, (
            f"Expected {original_count * 2} total nodes, got {len(all_ids)}"
        )

        # All IDs should be unique (no collisions between original and pasted)
        assert len(set(all_ids)) == len(all_ids), (
            f"Duplicate IDs found: {[x for x in all_ids if all_ids.count(x) > 1]}"
        )

        net.delete()

    def test_pasted_edges_reference_new_nodes(
        self, selenium: MiminetTester, network: MiminetTestNetwork
    ):
        """Pasted edges should connect pasted nodes, not original ones."""
        selenium.get(network.url)
        time.sleep(1)

        original_node_ids = {n["data"]["id"] for n in network.nodes}
        original_edge_count = len(network.edges)

        self._select_all(selenium)
        self._copy(selenium)
        self._paste(selenium)
        time.sleep(0.5)

        all_edges = network.edges
        new_edges = all_edges[original_edge_count:]

        for edge in new_edges:
            assert edge["data"]["source"] not in original_node_ids, (
                f"Pasted edge source {edge['data']['source']} references original node"
            )
            assert edge["data"]["target"] not in original_node_ids, (
                f"Pasted edge target {edge['data']['target']} references original node"
            )

    def test_pasted_jobs_copied(
        self, selenium: MiminetTester, network: MiminetTestNetwork
    ):
        """Jobs from original nodes should be copied to pasted nodes."""
        selenium.get(network.url)
        time.sleep(1)

        jobs_before = len(network.jobs)

        self._select_all(selenium)
        self._copy(selenium)
        self._paste(selenium)
        time.sleep(0.5)

        jobs_after = len(network.jobs)

        assert jobs_after == jobs_before * 2, (
            f"Expected {jobs_before * 2} jobs after paste, got {jobs_after}"
        )

    def test_paste_preserves_node_types(
        self, selenium: MiminetTester, network: MiminetTestNetwork
    ):
        """Pasted nodes should preserve their device types."""
        selenium.get(network.url)
        time.sleep(1)

        original_types = sorted([n["config"]["type"] for n in network.nodes])

        self._select_all(selenium)
        self._copy(selenium)
        self._paste(selenium)
        time.sleep(0.5)

        all_nodes = network.nodes
        new_nodes = all_nodes[len(original_types):]
        new_types = sorted([n["config"]["type"] for n in new_nodes])

        assert new_types == original_types, (
            f"Pasted node types {new_types} don't match original {original_types}"
        )

    def test_paste_multiple_times(
        self, selenium: MiminetTester, network: MiminetTestNetwork
    ):
        """Pasting multiple times should create multiple copies."""
        selenium.get(network.url)
        time.sleep(1)

        nodes_before = len(network.nodes)

        self._select_all(selenium)
        self._copy(selenium)

        # Paste 3 times
        self._paste(selenium)
        time.sleep(0.3)
        self._paste(selenium)
        time.sleep(0.3)
        self._paste(selenium)
        time.sleep(0.5)

        nodes_after = len(network.nodes)

        assert nodes_after == nodes_before * 4, (
            f"Expected {nodes_before * 4} nodes after 3 pastes, got {nodes_after}"
        )

    def test_copy_without_selection_does_nothing(
        self, selenium: MiminetTester, network: MiminetTestNetwork
    ):
        """Ctrl+C with no selection should not change internal clipboard."""
        selenium.get(network.url)
        time.sleep(1)

        # Clear any previous clipboard
        selenium.execute_script("internalClipboard = null")

        # Copy with nothing selected
        self._deselect_all(selenium)
        self._copy(selenium)

        clipboard = selenium.execute_script("return internalClipboard")
        assert clipboard is None, "Clipboard should be null when nothing is selected"

    def test_programmatic_select_and_copy(
        self, selenium: MiminetTester, network: MiminetTestNetwork
    ):
        """Programmatic selection of specific nodes, then copy/paste should work."""
        selenium.get(network.url)
        time.sleep(1)

        nodes = network.nodes
        if len(nodes) < 2:
            pytest.skip("Need at least 2 nodes")

        # Select first two nodes via JS
        selenium.execute_script("""
            global_cy.elements().unselect();
            global_cy.getElementById(arguments[0]).select();
            global_cy.getElementById(arguments[1]).select();
        """, nodes[0]["data"]["id"], nodes[1]["data"]["id"])
        time.sleep(0.3)

        selected = self._get_selected_count(selenium)
        assert selected == 2, f"Expected 2 selected, got {selected}"

        # Copy and paste the partial selection
        nodes_before = len(network.nodes)
        self._copy(selenium)
        self._paste(selenium)
        time.sleep(0.5)

        nodes_after = len(network.nodes)
        assert nodes_after == nodes_before + 2, (
            f"Expected {nodes_before + 2} nodes after partial paste, got {nodes_after}"
        )
