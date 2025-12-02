import pytest
from selenium.webdriver.common.by import By
from conftest import MiminetTester
from utils.networks import NodeType, MiminetTestNetwork
from utils.locators import Location


class TestFieldsFilter:

    @pytest.fixture(scope="function")
    def network(self, selenium: MiminetTester):
        # make simple network
        network = MiminetTestNetwork(selenium)
        network.add_node(NodeType.Host)
        network.add_node(NodeType.Router)

        network.add_edge(0, 1)

        yield network
        network.delete()

    def test_gateway_filtering(
        self, selenium: MiminetTester, network: MiminetTestNetwork
    ):
        """
        Checks that the Default Gateway field automatically filters commas (,)
        and letters "ю", replacing them with dot (.)
        """
        network.open_node_config(0)

        gw_selector = Location.Network.ConfigPanel.Host.DEFAULT_GATEWAY_FIELD.selector
        gw_input = selenium.find_element(By.CSS_SELECTOR, gw_selector)

        gw_input.clear()
        gw_input.send_keys("192,168ю1ю1")

        actual_value = gw_input.get_attribute("value")
        assert (
            actual_value == "192.168.1.1"
        ), f"The filter failed. Expected '192.168.1.1', received '{actual_value}'"

    def test_host_add_route_gateway_filter(
        self, selenium: MiminetTester, network: MiminetTestNetwork
    ):
        """
        Checks the input filtering in the Gateway field in add route
        """
        network.open_node_config(0)  # host

        # select job 102 command: add route
        selenium.select_by_value(
            By.CSS_SELECTOR,
            Location.Network.ConfigPanel.Host.JOB_SELECT.selector,
            "102",  # ip route add command ID
        )

        gw_input_id = "#config_host_add_route_gw_input_field"

        selenium.wait_until_appear(By.CSS_SELECTOR, gw_input_id)
        gw_element = selenium.find_element(By.CSS_SELECTOR, gw_input_id)

        gw_element.clear()
        gw_element.send_keys("10,10ю10ю1")

        assert (
            gw_element.get_attribute("value") == "10.10.10.1"
        ), "The gateway field filter did not work"

    def test_router_cidr_notation_add_ip(
        self, selenium: MiminetTester, network: MiminetTestNetwork
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
        self, selenium: MiminetTester, network: MiminetTestNetwork
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
        self, selenium: MiminetTester, network: MiminetTestNetwork
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
