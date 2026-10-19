"""Issue #503: a textbox must not reset the emulation in the editor.

CI starts no emulation backend for the E2E suite, so a finished emulation is
planted in the page the same way ``test_packet_filters.py`` does it. Every
textbox change then goes through the real UI -- drag from the tool panel, the
config form, the Delete key, Ctrl+Z -- and the player must survive it. The
server side of the fix is covered by ``front/tests/test_textbox_emulation.py``.
"""

import pytest
from playwright.sync_api import Page, expect

from utils.locators import Location
from utils.networks import MiminetTestNetwork, NodeType

PLANT_EMULATION = """
    () => {
        packetsNotFiltered = null;
        packets = [[{
            data: {id: 'pkt_1', label: 'ICMP echo-request'},
            config: {type: 'ICMP echo-request', path: '', source: 'host_1', target: 'host_1'},
        }]];
        pcaps = [];
        SetNetworkPlayerState(0);
    }
"""


@pytest.fixture
def network(authorized_page: Page):
    """A network that holds a finished emulation."""
    network = MiminetTestNetwork(authorized_page)
    network.add_node(NodeType.Host)

    authorized_page.evaluate(PLANT_EMULATION)
    _assert_emulation_kept(authorized_page)

    yield network

    network.delete()


def _assert_emulation_kept(page: Page):
    assert page.evaluate("packets !== null && packets.length === 1"), (
        "The emulation was reset"
    )
    expect(
        page.locator(Location.Network.EMULATE_PLAYER_PAUSE_BUTTON.selector)
    ).to_be_visible()


def _assert_emulation_reset(page: Page):
    assert page.evaluate("packets === null"), "The emulation was kept"
    expect(page.locator(Location.Network.EMULATE_BUTTON.selector)).to_be_visible()


def _add_textbox(page: Page, network: MiminetTestNetwork) -> str:
    page.click(Location.Network.ToolPanel.TOGGLE.selector)
    network.add_node(Location.Network.ToolPanel.TEXTBOX.selector, 50, 20)
    textbox = next(n for n in network.nodes if n["config"]["type"] == "textbox")
    return textbox["data"]["id"]


def _click_node(page: Page, node_id: str):
    """Tap a node on the canvas: selects it and opens its config form."""
    panel = page.locator(Location.Network.MAIN_PANEL.selector).bounding_box()
    assert panel is not None
    pos = page.evaluate(f"global_cy.getElementById('{node_id}').renderedPosition()")
    page.mouse.click(panel["x"] + pos["x"], panel["y"] + pos["y"])


def test_adding_textbox_keeps_emulation(authorized_page: Page, network):
    _add_textbox(authorized_page, network)

    _assert_emulation_kept(authorized_page)


def test_editing_textbox_keeps_emulation(authorized_page: Page, network):
    textbox_id = _add_textbox(authorized_page, network)
    form = Location.Network.ConfigPanel.Textbox

    _click_node(authorized_page, textbox_id)
    authorized_page.fill(form.CONTENT_FIELD.selector, "a note on the network")
    authorized_page.click(form.SUBMIT_BUTTON.selector)
    authorized_page.wait_for_function(
        "nodes.some(n => n.config.label === 'a note on the network')"
    )

    _assert_emulation_kept(authorized_page)


def test_deleting_textbox_keeps_emulation(authorized_page: Page, network):
    textbox_id = _add_textbox(authorized_page, network)

    _click_node(authorized_page, textbox_id)
    authorized_page.keyboard.press("Delete")
    authorized_page.wait_for_function(f"!nodes.some(n => n.data.id === '{textbox_id}')")

    _assert_emulation_kept(authorized_page)


def test_undoing_textbox_keeps_emulation(authorized_page: Page, network):
    textbox_id = _add_textbox(authorized_page, network)

    authorized_page.keyboard.press("Control+z")
    authorized_page.wait_for_function(f"!nodes.some(n => n.data.id === '{textbox_id}')")

    _assert_emulation_kept(authorized_page)


def test_adding_device_still_resets_emulation(authorized_page: Page, network):
    """Control: without it the cases above would pass if nothing reset at all."""
    network.add_node(NodeType.Host)

    _assert_emulation_reset(authorized_page)


def test_undoing_device_still_resets_emulation(authorized_page: Page, network):
    """Control for undo: the emulation of a network with the host is stale
    once the host is undone."""
    network.add_node(NodeType.Host)
    authorized_page.evaluate(PLANT_EMULATION)
    _assert_emulation_kept(authorized_page)

    authorized_page.keyboard.press("Control+z")
    authorized_page.wait_for_function("nodes.length === 1")

    _assert_emulation_reset(authorized_page)
