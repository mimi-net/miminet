import pytest
from selenium.webdriver.common.by import By

from conftest import MiminetTester
from utils.locators import Location
from utils.networks import MiminetTestNetwork
from enum import Enum


class TestPacketFilters:
    class Filter(Enum):
        ARP = "ARP"
        STP = "STP"
        SYN = "SYN"

    @pytest.fixture(scope="class")
    def network(self, selenium: MiminetTester):
        test_network = MiminetTestNetwork(selenium)
        yield test_network
        test_network.delete()

    def _wait_filter_state_ready(self, selenium: MiminetTester):
        selenium.wait_for(
            lambda driver: driver.execute_script(
                "return typeof packetFilterState !== 'undefined' && "
                "typeof SetPacketFilter === 'function';"
            )
        )

    def _open_settings_modal(self, selenium: MiminetTester):
        selenium.find_element(
            By.CSS_SELECTOR, Location.Network.TopButton.OPTIONS.selector
        ).click()
        selenium.wait_until_appear(By.CSS_SELECTOR, "#netConfigModal")

    def _save_network_options(self, selenium: MiminetTester):
        submit_button = selenium.find_element(
            By.CSS_SELECTOR, Location.Network.Options.SUBMIT_BUTTON.selector
        )
        submit_button.click()
        selenium.wait_for(
            lambda driver: driver.execute_script(
                "return !document.querySelector('#netConfigModal')"
                " || $('#netConfigModal').is(':hidden');"
            )
        )

    def _close_options_modal(
        self, selenium: MiminetTester, cancel_button_id="networkConfigurationCancel"
    ):
        if selenium.execute_script(
            "return !document.querySelector('#netConfigModal')"
            " || $('#netConfigModal').is(':hidden');"
        ):
            return
        cancel_button = selenium.find_element(By.ID, cancel_button_id)
        cancel_button.click()
        selenium.wait_for(
            lambda driver: driver.execute_script(
                "return !document.querySelector('#netConfigModal')"
                " || $('#netConfigModal').is(':hidden');"
            )
        )

    def _checkbox_state(self, selenium: MiminetTester, checkbox_id: str):
        return selenium.execute_script(
            f"var el = document.getElementById('{checkbox_id}');"
            "return el ? el.checked : null;"
        )

    def _prepare_packets(self, selenium: MiminetTester, labels: list[str]):
        selenium.execute_script(
            """
            packetFilterState.hideARP = false;
            packetFilterState.hideSTP = false;
            packetFilterState.hideSYN = false;
            packetsNotFiltered = null;
            packets = arguments[0].map(function(label){ return [{ data: { label: label } }]; });
            pcaps = [];
            """,
            labels,
        )

    def _find_filter(self, selenium, filter_name: Filter):
        return selenium.find_element(
            By.CSS_SELECTOR, f"{filter_name.value}FilterCheckbox"
        )

    def test_enable_arp_filter_filters_packets(
        self, selenium: MiminetTester, network: MiminetTestNetwork
    ):
        selenium.get(network.url)
        self._wait_filter_state_ready(selenium)

        self._prepare_packets(selenium, ["ARP packet", "ICMP packet"])

        self._open_settings_modal(selenium)
        arp_checkbox = self._find_filter(selenium, self.Filter.ARP)
        if not arp_checkbox.is_selected():
            arp_checkbox.click()
        self._save_network_options(selenium)
        self._close_options_modal(selenium)
        selenium.wait_for(
            lambda driver: driver.execute_script(
                "return packetFilterState.hideARP === true"
                " && Array.isArray(packets)"
                " && packets.length === 1"
                " && packets[0].length === 1"
                " && !packets[0][0].data.label.startsWith('ARP');"
            )
        )

        filtered_packets = selenium.execute_script("return packets;")
        assert filtered_packets[0][0]["data"]["label"] == "ICMP packet"

        self._open_settings_modal(selenium)
        assert (
            self._checkbox_state(selenium, "ARPFilterCheckbox") is True
        ), "ARP checkbox should remain selected after saving"
        self._close_options_modal(selenium)

    def test_cancel_does_not_change_filter_state(
        self, selenium: MiminetTester, network: MiminetTestNetwork
    ):
        selenium.get(network.url)
        self._wait_filter_state_ready(selenium)

        initial_state = selenium.execute_script(
            "return packetFilterState.hideARP === true;"
        )

        self._open_settings_modal(selenium)
        arp_checkbox = self._find_filter(selenium, self.Filter.ARP)
        arp_checkbox.click()  # toggle current state
        self._close_options_modal(selenium)  # close without saving

        current_state = selenium.execute_script(
            "return packetFilterState.hideARP === true;"
        )
        assert (
            current_state == initial_state
        ), "Filter state must not change when closing without saving"

        self._open_settings_modal(selenium)
        assert (
            self._checkbox_state(selenium, "ARPFilterCheckbox") == initial_state
        ), "ARP checkbox should display the original value after cancel"
        self._close_options_modal(selenium)

    def test_enable_stp_filter_filters_packets(
        self, selenium: MiminetTester, network: MiminetTestNetwork
    ):
        selenium.get(network.url)
        self._wait_filter_state_ready(selenium)

        self._prepare_packets(
            selenium,
            [
                "STP packet",
                "RSTP packet",
                "ICMP packet",
            ],
        )

        self._open_settings_modal(selenium)
        stp_checkbox = self._find_filter(selenium, self.Filter.STP)
        if not stp_checkbox.is_selected():
            stp_checkbox.click()
        self._save_network_options(selenium)
        self._close_options_modal(selenium)

        selenium.wait_for(
            lambda driver: driver.execute_script(
                "return packetFilterState.hideSTP === true"
                " && Array.isArray(packets)"
                " && packets.length === 1"
                " && packets[0].length === 1"
                " && !packets[0][0].data.label.startsWith('STP')"
                " && !packets[0][0].data.label.startsWith('RSTP');"
            )
        )

        filtered_packets = selenium.execute_script("return packets;")
        assert filtered_packets[0][0]["data"]["label"] == "ICMP packet"

        self._open_settings_modal(selenium)
        assert (
            self._checkbox_state(selenium, "STPFilterCheckbox") is True
        ), "STP checkbox should remain selected after saving"
        self._close_options_modal(selenium)

    def test_enable_syn_filter_filters_packets(
        self, selenium: MiminetTester, network: MiminetTestNetwork
    ):
        selenium.get(network.url)
        self._wait_filter_state_ready(selenium)
        self._prepare_packets(
            selenium,
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

        self._open_settings_modal(selenium)
        syn_checkbox = self._find_filter(selenium, self.Filter.SYN)
        if not syn_checkbox.is_selected():
            syn_checkbox.click()
        self._save_network_options(selenium)
        self._close_options_modal(selenium)

        selenium.wait_for(
            lambda driver: driver.execute_script(
                "return packetFilterState.hideSYN === true"
                " && Array.isArray(packets)"
                " && packets.length === 1"
                " && packets[0].length === 1;"
            )
        )

        filtered_packets = selenium.execute_script("return packets;")
        assert filtered_packets[0][0]["data"]["label"] == "TCP (PUSH + ACK)"

        self._open_settings_modal(selenium)
        assert (
            self._checkbox_state(selenium, Location.Network.Options.SYN_FILTER.selector)
            is True
        ), "SYN checkbox should remain selected after saving"
        self._close_options_modal(selenium)

    def test_disabling_filters_restores_packets(
        self, selenium: MiminetTester, network: MiminetTestNetwork
    ):
        selenium.get(network.url)
        self._wait_filter_state_ready(selenium)

        self._prepare_packets(
            selenium,
            [
                "ARP packet",
                "STP packet",
                "TCP (SYN)",
            ],
        )

        # Enable all filters and apply
        self._open_settings_modal(selenium)
        arp_checkbox = self._find_filter(selenium, self.Filter.ARP)
        stp_checkbox = self._find_filter(selenium, self.Filter.STP)
        syn_checkbox = self._find_filter(selenium, self.Filter.SYN)
        if not arp_checkbox.is_selected():
            arp_checkbox.click()
        if not stp_checkbox.is_selected():
            stp_checkbox.click()
        if not syn_checkbox.is_selected():
            syn_checkbox.click()
        self._save_network_options(selenium)
        self._close_options_modal(selenium)

        selenium.wait_for(
            lambda driver: driver.execute_script(
                "return packetFilterState.hideARP === true"
                " && packetFilterState.hideSTP === true"
                " && packetFilterState.hideSYN === true"
                " && Array.isArray(packets)"
                " && packets.length === 0;"
            )
        )

        # Disable filters and ensure packets come back
        self._open_settings_modal(selenium)
        arp_checkbox = self._find_filter(selenium, self.Filter.ARP)
        stp_checkbox = self._find_filter(selenium, self.Filter.STP)
        syn_checkbox = self._find_filter(selenium, self.Filter.SYN)
        if arp_checkbox.is_selected():
            arp_checkbox.click()
        if stp_checkbox.is_selected():
            stp_checkbox.click()
        if syn_checkbox.is_selected():
            syn_checkbox.click()
        self._save_network_options(selenium)
        self._close_options_modal(selenium)

        selenium.wait_for(
            lambda driver: driver.execute_script(
                "return packetFilterState.hideARP === false"
                " && packetFilterState.hideSTP === false"
                " && packetFilterState.hideSYN === false"
                " && Array.isArray(packets)"
                " && packets.length === 3;"
            )
        )
