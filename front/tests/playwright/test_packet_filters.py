from enum import Enum

import pytest
from playwright.sync_api import Page

from utils.locators import Location
from utils.networks import MiminetTestNetwork

MODAL_HIDDEN = (
    "!document.querySelector('#netConfigModal') || $('#netConfigModal').is(':hidden')"
)


class TestPacketFilters:
    class Filter(Enum):
        ARP = Location.Network.Options.ARP_FILTER
        STP = Location.Network.Options.STP_FILTER
        SYN = Location.Network.Options.SYN_FILTER

    @pytest.fixture(scope="class")
    def network(self, authorized_page: Page):
        test_network = MiminetTestNetwork(authorized_page)
        yield test_network

        # A dialog left open would swallow the clicks the deletion needs. The
        # Selenium version retries the whole deletion through JS after an
        # ElementClickInterceptedException; here the overlay is simply dismissed
        # first, and Playwright's actionability checks wait out the animation.
        try:
            authorized_page.evaluate("$('.modal.show').modal('hide');")
        except Exception:
            pass

        try:
            test_network.delete()
        except Exception:
            pass

    def _wait_filter_state_ready(self, page: Page):
        page.wait_for_function(
            "typeof packetFilterState !== 'undefined' && "
            "typeof SetPacketFilter === 'function'"
        )

    def _open_settings_modal(self, page: Page):
        page.click(Location.Network.TopButton.OPTIONS.selector)
        page.wait_for_selector("#netConfigModal")
        self._wait_filters_ready(page)

    def _wait_filters_ready(self, page: Page):
        for locator in (
            Location.Network.Options.ARP_FILTER,
            Location.Network.Options.STP_FILTER,
            Location.Network.Options.SYN_FILTER,
        ):
            page.wait_for_selector(locator.selector)

    def _save_network_options(self, page: Page):
        page.click(Location.Network.Options.SUBMIT_BUTTON.selector)
        page.wait_for_function(MODAL_HIDDEN)

    def _close_options_modal(
        self, page: Page, cancel_button_id="networkConfigurationCancel"
    ):
        if page.evaluate(MODAL_HIDDEN):
            return
        page.click(f"#{cancel_button_id}")
        page.wait_for_function(MODAL_HIDDEN)

    def _checkbox_state(self, page: Page, checkbox_id: str):
        return page.evaluate(
            f"document.getElementById('{checkbox_id}')"
            f" ? document.getElementById('{checkbox_id}').checked : null"
        )

    def _prepare_packets(self, page: Page, labels: list[str]):
        page.evaluate(
            """
            (labels) => {
                packetFilterState.hideARP = false;
                packetFilterState.hideSTP = false;
                packetFilterState.hideSYN = false;
                packetsNotFiltered = null;
                packets = labels.map(function(label){ return [{ data: { label: label } }]; });
                pcaps = [];
            }
            """,
            labels,
        )

    def _set_filter(
        self, page: Page, filter: "TestPacketFilters.Filter", enabled: bool
    ):
        """Bring a filter checkbox to ``enabled``, clicking only when needed."""
        checkbox = page.locator(filter.value.selector)
        checkbox.wait_for(state="visible")
        if checkbox.is_checked() != enabled:
            checkbox.click()

    def test_enable_arp_filter_filters_packets(
        self, authorized_page: Page, network: MiminetTestNetwork
    ):
        authorized_page.goto(network.url)
        self._wait_filter_state_ready(authorized_page)

        self._prepare_packets(authorized_page, ["ARP packet", "ICMP packet"])

        self._open_settings_modal(authorized_page)
        self._set_filter(authorized_page, self.Filter.ARP, True)
        self._save_network_options(authorized_page)
        self._close_options_modal(authorized_page)

        authorized_page.wait_for_function(
            "packetFilterState.hideARP === true"
            " && Array.isArray(packets)"
            " && packets.length === 1"
            " && packets[0].length === 1"
            " && !packets[0][0].data.label.startsWith('ARP')"
        )

        filtered_packets = authorized_page.evaluate("packets")
        assert filtered_packets[0][0]["data"]["label"] == "ICMP packet"

        self._open_settings_modal(authorized_page)
        assert self._checkbox_state(authorized_page, "ARPFilterCheckbox") is True, (
            "ARP checkbox should remain selected after saving"
        )
        self._close_options_modal(authorized_page)

    def test_cancel_does_not_change_filter_state(
        self, authorized_page: Page, network: MiminetTestNetwork
    ):
        authorized_page.goto(network.url)
        self._wait_filter_state_ready(authorized_page)

        initial_state = authorized_page.evaluate("packetFilterState.hideARP === true")

        self._open_settings_modal(authorized_page)
        # toggle current state
        authorized_page.locator(self.Filter.ARP.value.selector).click()
        self._close_options_modal(authorized_page)  # close without saving

        current_state = authorized_page.evaluate("packetFilterState.hideARP === true")
        assert current_state == initial_state, (
            "Filter state must not change when closing without saving"
        )

        self._open_settings_modal(authorized_page)
        assert (
            self._checkbox_state(authorized_page, "ARPFilterCheckbox") == initial_state
        ), "ARP checkbox should display the original value after cancel"
        self._close_options_modal(authorized_page)

    def test_enable_stp_filter_filters_packets(
        self, authorized_page: Page, network: MiminetTestNetwork
    ):
        authorized_page.goto(network.url)
        self._wait_filter_state_ready(authorized_page)

        self._prepare_packets(
            authorized_page,
            [
                "STP packet",
                "RSTP packet",
                "ICMP packet",
            ],
        )

        self._open_settings_modal(authorized_page)
        self._set_filter(authorized_page, self.Filter.STP, True)
        self._save_network_options(authorized_page)
        self._close_options_modal(authorized_page)

        authorized_page.wait_for_function(
            "packetFilterState.hideSTP === true"
            " && Array.isArray(packets)"
            " && packets.length === 1"
            " && packets[0].length === 1"
            " && !packets[0][0].data.label.startsWith('STP')"
            " && !packets[0][0].data.label.startsWith('RSTP')"
        )

        filtered_packets = authorized_page.evaluate("packets")
        assert filtered_packets[0][0]["data"]["label"] == "ICMP packet"

        self._open_settings_modal(authorized_page)
        assert self._checkbox_state(authorized_page, "STPFilterCheckbox") is True, (
            "STP checkbox should remain selected after saving"
        )
        self._close_options_modal(authorized_page)

    def test_enable_syn_filter_filters_packets(
        self, authorized_page: Page, network: MiminetTestNetwork
    ):
        authorized_page.goto(network.url)
        self._wait_filter_state_ready(authorized_page)
        self._prepare_packets(
            authorized_page,
            [
                "TCP (SYN)",
                "TCP (SYN + ACK)",
                "TCP (ACK)",
                "TCP (PUSH + ACK)",
                "TCP (FIN + ACK)",
                "TCP (ACK)",
                "TCP (FIN + ACK)",
                "TCP (ACK)",
            ],
        )

        self._open_settings_modal(authorized_page)
        self._set_filter(authorized_page, self.Filter.SYN, True)
        self._save_network_options(authorized_page)
        self._close_options_modal(authorized_page)

        authorized_page.wait_for_function(
            "packetFilterState.hideSYN === true"
            " && Array.isArray(packets)"
            " && packets.length === 1"
            " && packets[0].length === 1"
        )

        filtered_packets = authorized_page.evaluate("packets")
        assert filtered_packets[0][0]["data"]["label"] == "TCP (PUSH + ACK)"

        self._open_settings_modal(authorized_page)
        assert self._checkbox_state(authorized_page, "SYNFilterCheckbox") is True, (
            "SYN checkbox should remain selected after saving"
        )
        self._close_options_modal(authorized_page)

    def test_disabling_filters_restores_packets(
        self, authorized_page: Page, network: MiminetTestNetwork
    ):
        authorized_page.goto(network.url)
        self._wait_filter_state_ready(authorized_page)

        self._prepare_packets(
            authorized_page,
            [
                "ARP packet",
                "STP packet",
                "TCP (SYN)",
            ],
        )

        # Enable all filters and apply
        self._open_settings_modal(authorized_page)
        for filter in (self.Filter.ARP, self.Filter.STP, self.Filter.SYN):
            self._set_filter(authorized_page, filter, True)
        self._save_network_options(authorized_page)
        self._close_options_modal(authorized_page)

        authorized_page.wait_for_function(
            "packetFilterState.hideARP === true"
            " && packetFilterState.hideSTP === true"
            " && packetFilterState.hideSYN === true"
            " && Array.isArray(packets)"
            " && packets.length === 0"
        )

        # Disable filters and ensure packets come back
        self._open_settings_modal(authorized_page)
        for filter in (self.Filter.ARP, self.Filter.STP, self.Filter.SYN):
            self._set_filter(authorized_page, filter, False)
        self._save_network_options(authorized_page)
        self._close_options_modal(authorized_page)

        authorized_page.wait_for_function(
            "packetFilterState.hideARP === false"
            " && packetFilterState.hideSTP === false"
            " && packetFilterState.hideSYN === false"
            " && Array.isArray(packets)"
            " && packets.length === 3"
        )
