import pytest
from playwright.sync_api import Page

from utils.locators import Location
from utils.networks import MiminetTestNetwork, NodeType, type_sequentially


class TestFieldsFilter:
    @pytest.fixture(scope="function")
    def network(self, authorized_page: Page):
        # make simple network
        network = MiminetTestNetwork(authorized_page)
        network.add_node(NodeType.Host)
        network.add_node(NodeType.Router)

        network.add_edge(0, 1)

        yield network
        network.delete()

    def test_gateway_filtering(
        self, authorized_page: Page, network: MiminetTestNetwork
    ):
        """
        Checks that the Default Gateway field automatically filters commas (,)
        and letters "ю", replacing them with dot (.)
        """
        network.open_node_config(0)

        gw_selector = Location.Network.ConfigPanel.Host.DEFAULT_GATEWAY_FIELD.selector

        # Typed one character at a time: the filter runs on key events, so a
        # value set in a single shot would not exercise it.
        actual_value = type_sequentially(authorized_page, gw_selector, "192,168ю1ю1")

        assert actual_value == "192.168.1.1", (
            f"The filter failed. Expected '192.168.1.1', received '{actual_value}'"
        )

    def test_host_add_route_gateway_filter(
        self, authorized_page: Page, network: MiminetTestNetwork
    ):
        """
        Checks the input filtering in the Gateway field in add route
        """
        network.open_node_config(0)  # host

        # select job 102 command: add route
        authorized_page.select_option(
            Location.Network.ConfigPanel.Host.JOB_SELECT.selector,
            value="102",  # ip route add command ID
        )

        gw_input_id = "#config_host_add_route_gw_input_field"

        actual_value = type_sequentially(authorized_page, gw_input_id, "10,10ю10ю1")

        assert actual_value == "10.10.10.1", "The gateway field filter did not work"

    def test_router_cidr_notation_add_ip(
        self, authorized_page: Page, network: MiminetTestNetwork
    ):
        """
        Checks adding an IP address using ip/mask in a single field
        """
        router_node = network.nodes[1]
        config = network.open_node_config(1)

        iface_id = router_node["interface"][0]["id"]

        # enter "10.0.0.1/24" in the ip field and leave the mask field empty
        config.add_jobs(
            100,
            {
                "#config_router_add_ip_mask_iface_select_field": iface_id,
                "#config_router_add_ip_mask_ip_input_field": "10.0.0.1/24",
                # skip mask
            },
        )

        last_job = network.jobs[-1]

        assert last_job["job_id"] == 100
        assert last_job["arg_2"] == "10.0.0.1", "IP address was not extracted correctly"
        assert last_job["arg_3"] == "24", "Mask was not extracted correctly from CIDR"

    def test_router_cidr_notation_add_route(
        self, authorized_page: Page, network: MiminetTestNetwork
    ):
        """
        Checks adding a route using ip/mask
        """
        config = network.open_node_config(1)

        config.add_jobs(
            102,
            {
                Location.Network.ConfigPanel.Router.Job.ADD_ROUTE_IP_FIELD.selector: "192.168.0.0/16",
                Location.Network.ConfigPanel.Router.Job.ADD_ROUTE_IP_GW_FIELD.selector: "10.0.0.254",
                # skip mask
            },
        )

        last_job = network.jobs[-1]

        assert last_job["job_id"] == 102
        assert last_job["arg_1"] == "192.168.0.0", "Route network IP parsed incorrectly"
        assert last_job["arg_2"] == "16", "Route mask parsed incorrectly"
        assert last_job["arg_3"] == "10.0.0.254", "Gateway does not match"

    def test_router_cidr_notation_subinterface(
        self, authorized_page: Page, network: MiminetTestNetwork
    ):
        """
        Checks adding a VLAN subinterface using ip/mask
        """
        router_node = network.nodes[1]
        config = network.open_node_config(1)
        iface_id = router_node["interface"][0]["id"]

        config.add_jobs(
            104,
            {
                "#config_router_add_subinterface_iface_select_field": iface_id,
                "#config_router_add_subinterface_ip_input_field": "172.16.5.1/30",
                "#config_router_add_subinterface_vlan_input_field": "100",
                # skip mask
            },
        )

        last_job = network.jobs[-1]

        assert last_job["job_id"] == 104
        assert last_job["arg_2"] == "172.16.5.1", "Subinterface IP parsed incorrectly"
        assert last_job["arg_3"] == "30", "Subinterface mask parsed incorrectly"
        assert last_job["arg_4"] == "100", "VLAN ID does not match"
