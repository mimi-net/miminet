import pytest
from playwright.sync_api import Page

from conftest import WAIT_UNTIL
from utils.locators import Location
from utils.networks import MiminetTestNetwork, NodeType


class TestDuplicateBasic:
    @pytest.fixture(scope="class")
    def network(self, authorized_page: Page):
        network = MiminetTestNetwork(authorized_page)
        h1 = network.add_node(NodeType.Host)
        h2 = network.add_node(NodeType.Host)
        network.add_edge(h1, h2)

        yield network
        network.delete()

    def test_duplicate_value(self, authorized_page: Page, network: MiminetTestNetwork):
        edge = network.edges[0]
        network.open_edge_config(edge)

        authorized_page.fill(
            Location.Network.ConfigPanel.Edge.DUPLICATE_FIELD.selector, "30"
        )

        authorized_page.click(Location.Network.ConfigPanel.Edge.SUBMIT_BUTTON.selector)

        authorized_page.wait_for_function("edges[0].data.duplicate_percentage === '30'")

        assert network.edges[0]["data"]["duplicate_percentage"] == "30"


class TestDuplicateCopyNetwork:
    @pytest.fixture(scope="class")
    def network(self, authorized_page: Page):
        network = MiminetTestNetwork(authorized_page)

        h1 = network.add_node(NodeType.Host)
        h2 = network.add_node(NodeType.Host)

        network.add_edge(h1, h2)

        edge = network.edges[0]
        network.open_edge_config(edge)
        authorized_page.fill(
            Location.Network.ConfigPanel.Edge.DUPLICATE_FIELD.selector, "50"
        )

        authorized_page.click(Location.Network.ConfigPanel.Edge.SUBMIT_BUTTON.selector)

        # The JS sets the in-memory edge value before the save XHR completes,
        # so poll the server (in-page fetch, no navigation) until the persisted
        # value is visible; otherwise the copy test may read the pre-save state.
        authorized_page.wait_for_function(
            """
            (url) => fetch(url, {cache: 'no-store', credentials: 'include'})
                .then(r => r.text())
                .then(html => {
                    const m = html.match(/var edges = (.+?);\\s*var jobs/);
                    if (!m) return false;
                    const dm = m[1].match(/duplicate_percentage['"]?\\s*:\\s*['"]?([0-9]+)['"]?/);
                    return dm ? dm[1] === '50' : false;
                })
                .catch(() => false)
            """,
            arg=network.url,
        )

        yield network
        network.delete()

    def test_duplicate_preserved_on_copy(
        self, authorized_page: Page, network: MiminetTestNetwork
    ):
        authorized_page.goto(network.url)

        initial_edges = network.edges

        authorized_page.click(Location.Network.TopButton.COPY.selector)

        # Picked by label, not by index: the first button in the dialog is the
        # close cross.
        authorized_page.click("#ModalCopy button:has-text('Перейти к редактированию')")

        authorized_page.wait_for_url(
            lambda url: url != network.url, wait_until=WAIT_UNTIL
        )

        copy_net = MiminetTestNetwork(authorized_page, authorized_page.url)

        assert copy_net.url != network.url

        assert copy_net.edges[0]["data"].get("duplicate_percentage") == initial_edges[
            0
        ]["data"].get("duplicate_percentage")

        copy_net.delete()
