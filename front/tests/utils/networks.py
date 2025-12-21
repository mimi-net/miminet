from selenium.webdriver.common.by import By
from utils.locators import Location
from conftest import HOME_PAGE, MiminetTester
import random
from typing import Optional, Type, Tuple
from selenium.common.exceptions import NoSuchElementException
from json import dumps as json_dumps
from selenium.webdriver.support.ui import Select


class NodeType:
    """Node types for testing purposes."""

    Host = (By.CSS_SELECTOR, Location.Network.DevicePanel.HOST.selector)
    Switch = (By.CSS_SELECTOR, Location.Network.DevicePanel.SWITCH.selector)
    Router = (By.CSS_SELECTOR, Location.Network.DevicePanel.ROUTER.selector)
    Hub = (By.CSS_SELECTOR, Location.Network.DevicePanel.HUB.selector)
    Server = (By.CSS_SELECTOR, Location.Network.DevicePanel.SERVER.selector)


class MiminetTestNetwork:
    """
    Represents a Miminet network created for testing purposes.
    You can easily configure your test networks using this class.
    """

    def __init__(self, selenium: MiminetTester, url: str = ""):
        self.__selenium = selenium

        if not url:
            self.__build_empty_network()
        else:
            selenium.get(url)
            self.__selenium = selenium
            self.__url = url

    def __check_page(self):
        if self.__selenium.current_url != self.__url:
            self.__selenium.get(self.__url)

    @property
    def url(self):
        """url to network page"""
        return self.__url

    @property
    def nodes(self) -> list:
        """Current network nodes (may change during network usage)."""
        self.__check_page()
        return self.__selenium.execute_script("return nodes")

    @property
    def edges(self) -> list:
        """Current network edges (may change during network usage)."""
        self.__check_page()
        return self.__selenium.execute_script("return edges")

    @property
    def jobs(self) -> list:
        """Current network jobs (may change during network usage)."""
        self.__check_page()
        return self.__selenium.execute_script("return jobs")

    def __calc_panel_offset(self, panel, x: float, y: float):
        """Calculates coordinates with offset within the Network Panel.

        Args:
        x (float): X-coordinate percentage within the panel (0-100).
        y (float): Y-coordinate percentage within the panel (0-100).

        Returns:
        tuple: A tuple containing the calculated X and Y pixel offsets relative to the panel center.
        """
        assert 0 <= x <= 100, "x must be in [0, 100] range"
        assert 0 <= y <= 100, "y must be in [0, 100] range"

        # calculate offset of coordinates inside panel
        panel_width, panel_height = panel.rect["width"], panel.rect["height"]
        panel_x, panel_y = panel.rect["x"], panel.rect["y"]

        center_x, center_y = panel_x + panel_width / 2, panel_y + panel_height / 2
        offset_x, offset_y = center_x - panel_x, center_y - panel_y

        margin_x = min(99, max(3, x))
        margin_y = min(99, max(3, y))

        return ((margin_x / 100) * panel_width) - offset_x, (
            (margin_y / 100) * panel_height
        ) - offset_y

    def __build_empty_network(self):
        """Create new network and clear it after use.

        Returns:
        (str) : Network URL
        """
        self.__selenium.get(HOME_PAGE)
        self.__selenium.find_element(
            By.CSS_SELECTOR, Location.MyNetworks.NEW_NETWORK_BUTTON.selector
        ).click()

        self.__url = self.__selenium.current_url

    def open_node_config(self, device_node: dict | int):
        """Opens the configuration menu for a specific node.

        Args:
            device_node (dict | int): Device node for which to open the configuration.

        Returns:
            NodeConfig: An instance of the NodeConfig class, providing access to the configuration menu.
        """

        if isinstance(device_node, int):
            node = self.nodes[device_node]
        else:
            node = device_node

        return NodeConfig(self.__selenium, node)

    def open_edge_config(self, edge: dict):
        """Open configuration menu.

        Args:
            edge (dict): Edge for which the menu opens
        """
        self.__check_page()
        edge_id = edge["data"]["id"]
        self.__selenium.execute_script(f"ShowEdgeConfig('{edge_id}')")

        self.__selenium.wait_until_appear(
            By.CSS_SELECTOR, Location.Network.CONFIG_PANEL.selector
        )

    def add_node(
        self,
        node_type: tuple[str, str],
        x: Optional[float] = None,
        y: Optional[float] = None,
    ) -> int:
        """Add a new device node.

        Args:
            node_type (tuple[str, str]): Locator for the device button.
            x (Optional[float]): X-coordinate percentage within the panel (0-100). Defaults to a random value.
            y (Optional[float]): Y-coordinate percentage within the panel (0-100). Defaults to a random value.

        Returns:
            Id of the added node.
        """
        self.__check_page()
        old_nodes_len = len(self.nodes)

        panel = self.__selenium.find_element(
            By.CSS_SELECTOR, Location.Network.MAIN_PANEL.selector
        )

        x = x if x is not None else random.uniform(0, 100)
        y = y if y is not None else random.uniform(0, 100)

        local_x, local_y = self.__calc_panel_offset(panel, x, y)

        device_button = self.__selenium.find_element(*node_type)
        self.__selenium.drag_and_drop(device_button, panel, local_x, local_y)
        self.__selenium.wait_for(lambda _: old_nodes_len < len(self.nodes), timeout=5)
        return len(self.nodes) - 1

    def add_edge(self, source_id: int, target_id: int) -> int:
        self.__check_page()
        old_edges_len = len(self.edges)

        source_node, target_node = (
            self.nodes[source_id],
            self.nodes[target_id],
        )

        source_data_id = str(source_node["data"]["id"])
        target_data_id = str(target_node["data"]["id"])

        self.__selenium.execute_script(
            f"AddEdge('{source_data_id}', '{target_data_id}')"
        )
        self.__selenium.execute_script("DrawGraph()")
        self.__selenium.execute_script("PostNodesEdges()")

        self.__selenium.wait_for(lambda d: old_edges_len < len(self.edges))
        return len(self.edges) - 1

    def get_nodes_by_class(self, device_class: str) -> list[dict]:
        self.__check_page()
        filtered_nodes = list(
            filter(lambda node: node["classes"][0] == device_class, self.nodes)
        )

        assert len(filtered_nodes) != 0, f"Can't find device node for {device_class}!!!"

        return filtered_nodes

    def run_emulation(self) -> dict:
        """Run miminet emulation.

        [!] This function doesn't work in CI for unknown reasons :(.

        :Return: Emulation packets."""
        self.__check_page()
        self.__selenium.find_element(
            By.CSS_SELECTOR, Location.Network.EMULATE_BUTTON.selector
        ).click()
        self.__selenium.wait_until_appear(
            By.CSS_SELECTOR,
            Location.Network.EMULATE_PLAYER_PAUSE_BUTTON.selector,
            60,
        )

        packets = self.__selenium.execute_script("return packets")

        return packets

    def delete(self):
        """Delete current network."""
        self.__check_page()

        self.__selenium.find_element(
            By.CSS_SELECTOR, Location.Network.TopButton.OPTIONS.selector
        ).click()

        self.__selenium.wait_and_click(
            By.CSS_SELECTOR,
            Location.Network.ModalButton.DELETE_MODAL_BUTTON.selector,
        )
        self.__selenium.wait_and_click(
            By.CSS_SELECTOR,
            Location.Network.ModalButton.DELETE_SUBMIT_BUTTON.selector,
        )


class NodeConfig:
    """
    Represents a node configuration panel.
    You can easily add new jobs, links or set different values.
    """

    def __init__(self, selenium: MiminetTester, node: dict):
        self.__selenium = selenium
        # Locator with config elements
        self.__config_locator: Type[Location.Network.ConfigPanel.CommonDevice] = (
            Location.Network.ConfigPanel.Host
        )
        self.__node = node
        self.__open_config(node)

    @property
    def name(self):
        """Current name of the network device displayed in the configuration."""
        name = self.__selenium.find_element(
            By.CSS_SELECTOR, self.__config_locator.NAME_FIELD.selector
        ).get_attribute("value")

        return name

    @property
    def default_gw(self):
        """Current default gateway of the network device displayed in the configuration."""
        gw = self.__selenium.find_element(
            By.CSS_SELECTOR, self.__config_locator.DEFAULT_GATEWAY_FIELD.selector
        ).get_attribute("value")

        return gw

    def fill_link(self, ip: str, mask: int, link_id: int = 0):
        """Fill link (in config panel) with ip address and mask.

        Args:
            link_id: Link number in the config list (starts from 0)."""
        self.__check_config_open()

        try:
            self.__selenium.find_element(
                By.XPATH, Location.Network.ConfigPanel.get_ip_field_xpath(link_id)
            ).send_keys(ip)
            self.__selenium.find_element(
                By.XPATH, Location.Network.ConfigPanel.get_mask_field_xpath(link_id)
            ).send_keys(str(mask))
        except Exception:
            raise Exception("Unable to find link. Maybe you forgot to add edges.")

    def fill_links(self, ip_mask_list: list):
        """Fill multiple links (in config panel) with IP addresses and masks.

        Args:
            ip_mask_list: List of strings in the format "ip:mask".
        """
        self.__check_config_open()

        for link_id, ip_mask in enumerate(ip_mask_list):
            ip, mask = ip_mask.split(":")
            self.fill_link(ip, mask, link_id)

    def enable_stp(self, priority=10000):
        """Switch the FTP configuration toggle."""
        self.__check_config_open()

        self.__selenium.find_element(
            By.CSS_SELECTOR,
            Location.Network.ConfigPanel.Switch.RSTP_BUTTON.selector,
        ).click()

        modal_el = (
            By.CSS_SELECTOR,
            Location.Network.ConfigPanel.Switch.get_modal_dialog_selector(
                self.__node["data"]["id"]
            ),
        )

        with self.__selenium.run_in_modal_context(*modal_el) as dialog:
            dialog.find_element(
                By.CSS_SELECTOR,
                Location.Network.ConfigPanel.Switch.StpPanel.STP_BUTTON.selector,
            ).click()

            priority_field = dialog.find_element(
                By.CSS_SELECTOR,
                Location.Network.ConfigPanel.Switch.StpPanel.PRIORITY_FIELD.selector,
            )
            priority_field.clear()
            priority_field.send_keys(str(priority))

            dialog.find_element(
                By.CSS_SELECTOR,
                Location.Network.ConfigPanel.Switch.StpPanel.SUBMIT_BUTTON.selector,
            ).click()

    def disable_stp(self):
        """Switch the FTP configuration toggle."""
        self.__check_config_open()

        self.__selenium.find_element(
            By.CSS_SELECTOR,
            Location.Network.ConfigPanel.Switch.RSTP_BUTTON.selector,
        ).click()

        modal_el = (
            By.CSS_SELECTOR,
            Location.Network.ConfigPanel.Switch.get_modal_dialog_selector(
                self.__node["data"]["id"]
            ),
        )

        with self.__selenium.run_in_modal_context(*modal_el) as dialog:
            dialog.find_element(
                By.CSS_SELECTOR,
                Location.Network.ConfigPanel.Switch.StpPanel.OFF_STP_BUTTON.selector,
            ).click()

            dialog.find_element(
                By.CSS_SELECTOR,
                Location.Network.ConfigPanel.Switch.StpPanel.SUBMIT_BUTTON.selector,
            ).click()

    def add_jobs(self, job_id: int, args: dict[str, str], by=By.CSS_SELECTOR):
        """Adds a job to the system using Selenium.
        [!] Only for jobs that don't contain selection fields

        Args:
            job_id: The ID of the job (currently unused in the implementation).
            args: A dictionary where keys represent locators for job fields and values
                  represent the corresponding values to be entered.
        """
        self.__check_config_open()

        self.__select_job(job_id, by)

        for job_field, job_value in args.items():
            try:
                field_element = self.__selenium.find_element(by, job_field)

                if field_element.tag_name == "input":
                    field_element.clear()
                    field_element.send_keys(job_value)
                elif field_element.tag_name == "select":
                    self.__selenium.select_by_value(by, job_field, job_value)
                else:
                    raise Exception(f'Unknown tag "{field_element.tag_name}"')
            except Exception as e:
                raise ValueError(
                    f"Can't add job. Job's field: {job_field}, value: {job_value}. Error message: {str(e)}."
                )

        # press "enter" to save job and remove job menu
        try:
            self.submit()
        except Exception:
            raise ValueError("Can't add job. Check that the entered data is correct.")

    def fill_default_gw(self, ip: str):
        """Fill default gateway with data."""
        self.__check_config_open()

        assert (
            self.__config_locator.DEFAULT_GATEWAY_FIELD
        ), f'Unable to change default gateway for this element: "{self.__config_locator}".'

        gw_field = self.__selenium.find_element(
            By.CSS_SELECTOR, self.__config_locator.DEFAULT_GATEWAY_FIELD.selector
        )
        gw_field.clear()
        gw_field.send_keys(ip)

    def change_name(self, name: str):
        """Change device name."""
        self.__check_config_open()

        assert (
            self.__config_locator.NAME_FIELD
        ), f'Unable to change name for this element: "{self.__config_locator}".'

        name_field = self.__selenium.find_element(
            By.CSS_SELECTOR, self.__config_locator.NAME_FIELD.selector
        )
        name_field.clear()
        name_field.send_keys(name)

    def configure_vlan(self, fill_table: dict[str, Tuple[str, str]]):
        """Open and configure VLAN panel.

        Args:
            fill_table (dict[str, Tuple[str, str]]): Dictionary with structure { Device Name: (VLAN ID, Connection type) }
        """
        switch_name = self.name

        vlan_config_button = self.__selenium.find_element(
            By.CSS_SELECTOR, Location.Network.ConfigPanel.Switch.VLAN_BUTTON.selector
        )
        vlan_config_button.click()

        modal = (
            By.CSS_SELECTOR,
            Location.Network.ConfigPanel.Switch.VlanPanel.get_modal_dialog_selector(
                switch_name
            ),
        )

        with self.__selenium.run_in_modal_context(*modal) as dialog:
            switch_button = dialog.find_element(
                By.CSS_SELECTOR,
                Location.Network.ConfigPanel.Switch.VlanPanel.SWITCH_BUTTON.selector,
            )

            switch_button.click()

            # Go through each row
            row_id = 0
            while True:
                row_xpath = (
                    Location.Network.ConfigPanel.Switch.VlanPanel.get_table_row_xpath(
                        switch_name, row_id
                    )
                )

                if not self.__selenium.exist_element(By.XPATH, row_xpath):
                    # element out of table
                    break

                table_row_element = dialog.find_element(By.XPATH, row_xpath)
                row_elements = table_row_element.find_elements(By.TAG_NAME, "td")

                device_name = row_elements[0].text
                vlan_id_element = row_elements[1].find_element(By.TAG_NAME, "input")

                vlan_id, connection_type = fill_table[device_name]

                vlan_id_element.clear()
                vlan_id_element.send_keys(vlan_id)

                if device_name not in fill_table:
                    raise Exception(f"Can't find {device_name} in VLAN table.")

                connection_type_element = row_elements[2].find_element(
                    By.TAG_NAME, "select"
                )

                Select(connection_type_element).select_by_value(connection_type)

                row_id += 1

            # Save new table
            submit_button = dialog.find_element(
                By.CSS_SELECTOR,
                Location.Network.ConfigPanel.Switch.VlanPanel.SUBMIT_BUTTON.selector,
            )
            submit_button.click()

    def submit(self):
        """Submit configuration."""
        self.__check_config_open()

        self.__selenium.find_element(
            By.CSS_SELECTOR, self.__config_locator.SUBMIT_BUTTON.selector
        ).click()

        self.__selenium.wait_until_text(
            By.CSS_SELECTOR,
            self.__config_locator.SUBMIT_BUTTON.selector,
            self.__config_locator.SUBMIT_BUTTON.text,
            timeout=5,
        )

    def __select_job(self, job_id, by):
        if (
            self.__config_locator == Location.Network.ConfigPanel.Host
            or self.__config_locator == Location.Network.ConfigPanel.Router
            or self.__config_locator == Location.Network.ConfigPanel.Server
            or self.__config_locator == Location.Network.ConfigPanel.Switch
        ):
            self.__selenium.select_by_value(
                by, self.__config_locator.JOB_SELECT.selector, str(job_id)
            )
        else:
            raise ValueError(
                f"Can't add job. Node with type {self.__config_locator} can't use jobs"
            )

    def __open_config(self, node: dict):
        device_class = node["classes"][0]

        node_json = json_dumps(node)

        if device_class == Location.Network.DevicePanel.HOST.device_class:
            self.__selenium.execute_script(f"ShowHostConfig({node})")
            self.__config_locator = Location.Network.ConfigPanel.Host

        elif device_class == Location.Network.DevicePanel.SWITCH.device_class:
            self.__selenium.execute_script(f"ShowSwitchConfig({node_json})")
            self.__config_locator = Location.Network.ConfigPanel.Switch

        elif device_class == Location.Network.DevicePanel.HUB.device_class:
            self.__selenium.execute_script(f"ShowHubConfig({node})")
            self.__config_locator = Location.Network.ConfigPanel.Hub

        elif device_class == Location.Network.DevicePanel.ROUTER.device_class:
            self.__selenium.execute_script(f"ShowRouterConfig({node})")
            self.__config_locator = Location.Network.ConfigPanel.Router

        elif device_class == Location.Network.DevicePanel.SERVER.device_class:
            self.__selenium.execute_script(f"ShowServerConfig({node})")
            self.__config_locator = Location.Network.ConfigPanel.Server

        else:
            raise Exception("Can't find device type !!!")

        assert (
            self.__config_locator.MAIN_FORM
        ), f'Unable to open node config form for this element: "{self.__config_locator}".'

        self.__selenium.wait_until_appear(
            By.CSS_SELECTOR, self.__config_locator.MAIN_FORM.selector
        )

    def __check_config_open(self):
        """Check that the config is open and handle any errors."""
        try:
            self.__selenium.find_element(
                By.CSS_SELECTOR, self.__config_locator.MAIN_FORM.selector
            )
        except NoSuchElementException:
            raise Exception("Config panel isn't open during some operation.")

        # Collect error messages from modal dialogs
        error_msgs = [
            err_el.text
            for err_el in self.__selenium.find_elements(
                By.CSS_SELECTOR,
                Location.Network.ConfigPanel.MODAL_ERROR_DIALOG.selector,
            )
        ]

        if error_msgs:
            raise Exception(
                f"An error occurred while managing the config panel: {error_msgs}"
            )
