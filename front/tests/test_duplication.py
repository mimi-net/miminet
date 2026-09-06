import pytest
from conftest import MiminetTester
from selenium.webdriver.common.by import By
from utils.locators import Location
from utils.networks import MiminetTestNetwork, NodeType


def _server_edge_duplicate(
    selenium: MiminetTester, network: MiminetTestNetwork, expected: str
) -> bool:
    """Poll the server-rendered duplicate value via an in-page fetch.

    The edge-config form updates the in-memory JS graph before the save XHR
    completes. Reloading the page would abort that still-in-flight XHR, so a
    fresh copy of the network page is fetched from within the page itself and
    the served ``var edges`` literal is inspected instead.
    """
    script = """
        var url = arguments[0];
        var done = arguments[1];
        fetch(url, {cache: 'no-store', credentials: 'include'})
            .then(function (r) { return r.text(); })
            .then(function (html) {
                var m = html.match(/var edges = (.+?);\\s*var jobs/);
                if (!m) { done(null); return; }
                var dm = m[1].match(/duplicate_percentage['\"]?\\s*:\\s*['\"]?([0-9]+)['\"]?/);
                done(dm ? dm[1] : null);
            })
            .catch(function () { done(null); });
    """
    value = selenium.execute_async_script(script, network.url)
    return value == expected


class TestDuplicateBasic:
    @pytest.fixture(scope="class")
    def network(self, selenium: MiminetTester):
        network = MiminetTestNetwork(selenium)
        h1 = network.add_node(NodeType.Host)
        h2 = network.add_node(NodeType.Host)
        network.add_edge(h1, h2)

        yield network
        network.delete()

    def test_duplicate_value(
        self, selenium: MiminetTester, network: MiminetTestNetwork
    ):
        edge = network.edges[0]
        network.open_edge_config(edge)

        dup_field = selenium.find_element(
            By.CSS_SELECTOR, Location.Network.ConfigPanel.Edge.DUPLICATE_FIELD.selector
        )

        dup_field.clear()
        dup_field.send_keys("30")

        selenium.wait_and_click(
            By.CSS_SELECTOR,
            Location.Network.ConfigPanel.Edge.SUBMIT_BUTTON.selector,
        )

        selenium.wait_for(
            lambda _: network.edges[0]["data"].get("duplicate_percentage") == "30"
        )

        assert network.edges[0]["data"]["duplicate_percentage"] == "30"


class TestDuplicateCopyNetwork:
    @pytest.fixture(scope="class")
    def network(self, selenium: MiminetTester):
        network = MiminetTestNetwork(selenium)

        h1 = network.add_node(NodeType.Host)
        h2 = network.add_node(NodeType.Host)

        network.add_edge(h1, h2)

        edge = network.edges[0]
        network.open_edge_config(edge)
        selenium.find_element(
            By.CSS_SELECTOR, Location.Network.ConfigPanel.Edge.DUPLICATE_FIELD.selector
        ).send_keys("50")

        selenium.wait_and_click(
            By.CSS_SELECTOR,
            Location.Network.ConfigPanel.Edge.SUBMIT_BUTTON.selector,
        )

        # The JS sets the in-memory edge value before the save XHR completes,
        # so poll the server (in-page fetch, no navigation) until the persisted
        # value is visible; otherwise the copy test may read the pre-save state.
        selenium.wait_for(lambda _: _server_edge_duplicate(selenium, network, "50"))

        yield network
        network.delete()

    def test_duplicate_preserved_on_copy(
        self, selenium: MiminetTester, network: MiminetTestNetwork
    ):

        selenium.get(network.url)

        initial_edges = network.edges

        selenium.wait_and_click(
            By.CSS_SELECTOR, Location.Network.TopButton.COPY.selector
        )

        selenium.wait_until_appear(By.XPATH, Location.Network.MODAL_DIALOG.xpath)

        selenium.wait_and_click(
            By.XPATH, Location.Network.ModalButton.GO_TO_EDITING.xpath
        )

        copy_net = MiminetTestNetwork(selenium, selenium.current_url)

        assert copy_net.url != network.url

        assert copy_net.edges[0]["data"].get("duplicate_percentage") == initial_edges[
            0
        ]["data"].get("duplicate_percentage")
