import pytest
from selenium.webdriver.common.by import By

from conftest import MiminetTester
from utils.locators import Location
from utils.networks import MiminetTestNetwork


class TestPacketFilters:
    @pytest.fixture(scope="class")
    def network(self, selenium: MiminetTester):
        test_network = MiminetTestNetwork(selenium)
        yield test_network
        test_network.delete()

    def _wait_filter_state_ready(self, selenium: MiminetTester):
        selenium.wait_for(
            lambda driver: driver.execute_script(
                "return typeof filterState !== 'undefined' && "
                "typeof SetPacketFilter === 'function';"
            )
        )

    def _open_settings_modal(self, selenium: MiminetTester):
        selenium.find_element(
            By.CSS_SELECTOR, Location.Network.TopButton.OPTIONS.selector
        ).click()
        selenium.wait_until_appear(By.CSS_SELECTOR, "#netConfigModal")

    def _close_settings_modal(self, selenium: MiminetTester):
        selenium.execute_script("$('#netConfigModal').modal('hide');")
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
            filterState.hideARP = false;
            filterState.hideSTP = false;
            packets_not_filtered = null;
            packets = arguments[0].map(function(label){ return [{ data: { label: label } }]; });
            pcaps = [];
            """,
            labels,
        )

    def test_enable_arp_filter_filters_packets(
        self, selenium: MiminetTester, network: MiminetTestNetwork
    ):
        selenium.get(network.url)
        self._wait_filter_state_ready(selenium)

        self._prepare_packets(
            selenium, ["ARP Request: who-has 10.0.0.1", "ICMP Echo Reply"]
        )

        self._open_settings_modal(selenium)
        arp_checkbox = selenium.find_element(By.CSS_SELECTOR, "#ARPFilterCheckbox")
        if not arp_checkbox.is_selected():
            arp_checkbox.click()
        selenium.execute_script("UpdateNetworkConfig(); SetPacketFilter();")
        self._close_settings_modal(selenium)
        selenium.wait_for(
            lambda driver: driver.execute_script(
                "return filterState.hideARP === true"
                " && Array.isArray(packets)"
                " && packets.length === 1"
                " && packets[0].length === 1"
                " && !packets[0][0].data.label.startsWith('ARP');"
            )
        )

        filtered_packets = selenium.execute_script("return packets;")
        assert filtered_packets[0][0]["data"]["label"] == "ICMP Echo Reply"

        self._open_settings_modal(selenium)
        assert (
            self._checkbox_state(selenium, "ARPFilterCheckbox") is True
        ), "ARP checkbox should remain selected after saving"
        self._close_settings_modal(selenium)

    def test_cancel_does_not_change_filter_state(
        self, selenium: MiminetTester, network: MiminetTestNetwork
    ):
        selenium.get(network.url)
        self._wait_filter_state_ready(selenium)

        initial_state = selenium.execute_script("return filterState.hideARP === true;")

        self._open_settings_modal(selenium)
        arp_checkbox = selenium.find_element(By.CSS_SELECTOR, "#ARPFilterCheckbox")
        arp_checkbox.click()  # toggle current state
        self._close_settings_modal(selenium)

        current_state = selenium.execute_script("return filterState.hideARP === true;")
        assert (
            current_state == initial_state
        ), "Filter state must not change when closing without saving"

        self._open_settings_modal(selenium)
        assert (
            self._checkbox_state(selenium, "ARPFilterCheckbox") == initial_state
        ), "ARP checkbox should display the original value after cancel"
        self._close_settings_modal(selenium)

    def test_enable_stp_filter_filters_packets(
        self, selenium: MiminetTester, network: MiminetTestNetwork
    ):
        selenium.get(network.url)
        self._wait_filter_state_ready(selenium)

        self._prepare_packets(
            selenium,
            [
                "STP Configuration BPDU",
                "RSTP Topology Change",
                "ICMP Echo Reply",
            ],
        )

        self._open_settings_modal(selenium)
        stp_checkbox = selenium.find_element(By.CSS_SELECTOR, "#STPFilterCheckbox")
        if not stp_checkbox.is_selected():
            stp_checkbox.click()
        selenium.execute_script("UpdateNetworkConfig(); SetPacketFilter();")
        self._close_settings_modal(selenium)

        selenium.wait_for(
            lambda driver: driver.execute_script(
                "return filterState.hideSTP === true"
                " && Array.isArray(packets)"
                " && packets.length === 1"
                " && packets[0].length === 1"
                " && !packets[0][0].data.label.startsWith('STP')"
                " && !packets[0][0].data.label.startsWith('RSTP');"
            )
        )

        filtered_packets = selenium.execute_script("return packets;")
        assert filtered_packets[0][0]["data"]["label"] == "ICMP Echo Reply"

        self._open_settings_modal(selenium)
        assert (
            self._checkbox_state(selenium, "STPFilterCheckbox") is True
        ), "STP checkbox should remain selected after saving"
        self._close_settings_modal(selenium)
