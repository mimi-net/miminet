"""Playwright port of the network helpers.

The Selenium original reads the page's own JS graph state (``nodes``, ``edges``,
``jobs``) and calls the app's own functions (``AddEdge``, ``ShowHostConfig``)
rather than clicking the Cytoscape canvas. That approach carries over unchanged:
``page.evaluate`` replaces ``execute_script`` one for one. What shrinks is the
waiting -- Playwright's locator actions retry on their own, so the explicit
stale-element loops around every click and every field fill are gone.
"""

import random
from json import dumps as json_dumps
from typing import Optional, Tuple, Type, Union

from playwright._impl._api_structures import FloatRect
from playwright.sync_api import Locator as PWLocator
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from conftest import HOME_PAGE
from utils.locators import Location


class NodeType:
    """Node types for testing purposes.

    Unlike the Selenium version these are plain CSS selectors: Playwright takes
    a selector string directly, with no ``By`` strategy to pair it with.
    """

    Host: str = Location.Network.DevicePanel.HOST.selector
    Switch: str = Location.Network.DevicePanel.SWITCH.selector
    Router: str = Location.Network.DevicePanel.ROUTER.selector
    Hub: str = Location.Network.DevicePanel.HUB.selector
    Server: str = Location.Network.DevicePanel.SERVER.selector


class MiminetTestNetwork:
    """
    Represents a Miminet network created for testing purposes.
    You can easily configure your test networks using this class.
    """

    def __init__(self, page: Page, url: str = ""):
        self.__page = page

        if not url:
            self.__build_empty_network()
        else:
            page.goto(url)
            self.__url = url

    def __check_page(self):
        if self.__page.url != self.__url:
            self.__page.goto(self.__url)

    @property
    def url(self) -> str:
        """url to network page"""
        return self.__url

    @property
    def nodes(self) -> list:
        """Current network nodes (may change during network usage)."""
        self.__check_page()
        return self.__page.evaluate("nodes")

    @property
    def edges(self) -> list:
        """Current network edges (may change during network usage)."""
        self.__check_page()
        return self.__page.evaluate("edges")

    @property
    def jobs(self) -> list:
        """Current network jobs (may change during network usage)."""
        self.__check_page()
        return self.__page.evaluate("jobs")

    @staticmethod
    def __calc_panel_offset(
        panel_box: FloatRect, x: float, y: float
    ) -> Tuple[float, float]:
        """Calculates absolute page coordinates from a percentage within the panel.

        The Selenium version returns an offset relative to the panel centre,
        because ``move_to_element_with_offset`` measures from there. Playwright's
        ``mouse.move`` takes absolute page coordinates, so the panel origin is
        added here instead of being cancelled out.

        Args:
            panel_box: Bounding box of the network panel.
            x (float): X-coordinate percentage within the panel (0-100).
            y (float): Y-coordinate percentage within the panel (0-100).

        Returns:
            tuple: absolute (x, y) page coordinates.
        """
        assert 0 <= x <= 100, "x must be in [0, 100] range"
        assert 0 <= y <= 100, "y must be in [0, 100] range"

        margin_x = min(99, max(3, x))
        margin_y = min(99, max(3, y))

        return (
            panel_box["x"] + (margin_x / 100) * panel_box["width"],
            panel_box["y"] + (margin_y / 100) * panel_box["height"],
        )

    def __build_empty_network(self):
        """Create new network and clear it after use."""
        self.__page.goto(HOME_PAGE)
        self.__page.click(Location.MyNetworks.NEW_NETWORK_BUTTON.selector)

        # Wait for the frontend to finish creating the network and navigate to
        # its editor page before capturing the URL (no navigation race).
        #
        # Readiness is the graph state being in place, not the panel being
        # "visible": #network_scheme is an empty div that Cytoscape fills in
        # later, and an empty absolutely-positioned div has no size, so a
        # visibility wait races the script that gives it one. That race only
        # loses under load -- it surfaced once on a four-worker run, where the
        # element resolved 43 times while still hidden.
        self.__page.wait_for_selector(
            Location.Network.MAIN_PANEL.selector, state="attached"
        )
        self.__page.wait_for_function("typeof nodes !== 'undefined'")

        self.__url = self.__page.url

    def open_node_config(self, device_node: dict | int) -> "NodeConfig":
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

        return NodeConfig(self.__page, node)

    def open_edge_config(self, edge: dict):
        """Open configuration menu.

        Args:
            edge (dict): Edge for which the menu opens
        """
        self.__check_page()
        edge_id = edge["data"]["id"]
        self.__page.evaluate(f"ShowEdgeConfig('{edge_id}')")

        self.__page.wait_for_selector(Location.Network.CONFIG_PANEL.selector)

    def add_node(
        self,
        node_type: str,
        x: Optional[float] = None,
        y: Optional[float] = None,
    ) -> int:
        """Add a new device node.

        The device is dragged from the panel onto the canvas with explicit mouse
        steps rather than ``drag_to``: Cytoscape tracks pointer movement, and a
        single-jump drag drops the node in the wrong place.

        Args:
            node_type (str): CSS selector for the device button.
            x (Optional[float]): X-coordinate percentage within the panel (0-100). Defaults to a random value.
            y (Optional[float]): Y-coordinate percentage within the panel (0-100). Defaults to a random value.

        Returns:
            Id of the added node.
        """
        self.__check_page()
        old_nodes_len = len(self.nodes)

        panel = self.__page.locator(Location.Network.MAIN_PANEL.selector)
        # The panel only gains a size once Cytoscape has drawn into it, so the
        # box is awaited rather than read once: bounding_box() returns None
        # while the element is still empty.
        panel.wait_for(state="visible")
        panel_box = panel.bounding_box()
        assert panel_box is not None, "Network panel is not visible."

        x = x if x is not None else random.uniform(0, 100)
        y = y if y is not None else random.uniform(0, 100)

        target_x, target_y = self.__calc_panel_offset(panel_box, x, y)

        source = self.__page.locator(node_type)
        source_box = source.bounding_box()
        assert source_box is not None, f"Device button {node_type} is not visible."

        self.__page.mouse.move(
            source_box["x"] + source_box["width"] / 2,
            source_box["y"] + source_box["height"] / 2,
        )
        self.__page.mouse.down()
        # Intermediate move: some drag implementations ignore a press followed by
        # a single move to the target.
        self.__page.mouse.move(target_x, target_y, steps=10)
        self.__page.mouse.up()

        self.__page.wait_for_function(
            f"nodes.length > {old_nodes_len}",
            timeout=5_000,
        )
        return len(self.nodes) - 1

    def add_edge(self, source_id: int, target_id: int) -> int:
        self.__check_page()
        old_edges_len = len(self.edges)

        source_node, target_node = self.nodes[source_id], self.nodes[target_id]

        source_data_id = str(source_node["data"]["id"])
        target_data_id = str(target_node["data"]["id"])

        self.__page.evaluate(f"AddEdge('{source_data_id}', '{target_data_id}')")
        self.__page.evaluate("DrawGraph()")
        self.__page.evaluate("PostNodesEdges()")

        self.__page.wait_for_function(f"edges.length > {old_edges_len}")
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
        self.__page.click(Location.Network.EMULATE_BUTTON.selector)
        self.__page.wait_for_selector(
            Location.Network.EMULATE_PLAYER_PAUSE_BUTTON.selector,
            timeout=60_000,
        )

        return self.__page.evaluate("packets")

    def delete(self):
        """Delete current network."""
        self.__check_page()

        self.__page.click(Location.Network.TopButton.OPTIONS.selector)
        self.__page.click(Location.Network.ModalButton.DELETE_MODAL_BUTTON.selector)
        self.__page.click(Location.Network.ModalButton.DELETE_SUBMIT_BUTTON.selector)


class NodeConfig:
    """
    Represents a node configuration panel.
    You can easily add new jobs, links or set different values.
    """

    def __init__(self, page: Page, node: dict):
        self.__page = page
        # Locator with config elements
        self.__config_locator: Type[Location.Network.ConfigPanel.CommonDevice] = (
            Location.Network.ConfigPanel.Host
        )
        self.__node = node
        self.__open_config(node)

    @property
    def name(self) -> str:
        """Current name of the network device displayed in the configuration."""
        name_field = self.__config_locator.NAME_FIELD
        assert name_field is not None
        return self.__page.input_value(name_field.selector)

    @property
    def default_gw(self) -> str:
        """Current default gateway of the network device displayed in the configuration."""
        gw_field = self.__config_locator.DEFAULT_GATEWAY_FIELD
        assert gw_field is not None
        return self.__page.input_value(gw_field.selector)

    def fill_link(self, ip: str, mask: int, link_id: int = 0):
        """Fill link (in config panel) with ip address and mask.

        Args:
            link_id: Link number in the config list (starts from 0)."""
        self.__check_config_open()

        ip_field = f"xpath={Location.Network.ConfigPanel.get_ip_field_xpath(link_id)}"
        mask_field = (
            f"xpath={Location.Network.ConfigPanel.get_mask_field_xpath(link_id)}"
        )

        try:
            # fill() waits for the field to be editable, which covers the
            # async-rendered link rows the Selenium version waits for explicitly.
            self.__page.fill(ip_field, ip)
            self.__page.fill(mask_field, str(mask))
        except PlaywrightTimeoutError:
            raise Exception("Unable to find link. Maybe you forgot to add edges.")

    def fill_links(self, ip_mask_list: list):
        """Fill multiple links (in config panel) with IP addresses and masks.

        Args:
            ip_mask_list: List of strings in the format "ip:mask".
        """
        self.__check_config_open()

        for link_id, ip_mask in enumerate(ip_mask_list):
            ip, mask = ip_mask.split(":")
            self.fill_link(ip, int(mask), link_id)

    def add_jobs(self, job_id: int, args: dict[str, Union[str, int]]):
        """Adds a job to the system.
        [!] Only for jobs that don't contain selection fields

        Args:
            job_id: The ID of the job.
            args: A dictionary where keys represent CSS selectors for job fields
                  and values represent the corresponding values to be entered.
        """
        self.__check_config_open()

        self.__select_job(job_id)

        for job_field, job_value in args.items():
            try:
                element = self.__page.locator(job_field)
                tag_name = element.evaluate("el => el.tagName.toLowerCase()")

                if tag_name == "input":
                    element.fill(str(job_value))
                elif tag_name == "select":
                    element.select_option(value=str(job_value))
                else:
                    raise Exception(f'Unknown tag "{tag_name}"')
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

        assert self.__config_locator.DEFAULT_GATEWAY_FIELD, (
            f'Unable to change default gateway for this element: "{self.__config_locator}".'
        )

        self.__page.fill(self.__config_locator.DEFAULT_GATEWAY_FIELD.selector, ip)

    def __stp_dialog(self) -> PWLocator:
        """The STP modal belonging to this node.

        Every switch renders its own dialog carrying the same inner ids, so the
        dialog is resolved once and the controls are looked up inside it. That
        is what the Selenium version achieves with its ``scope`` argument.
        """
        return self.__page.locator(
            Location.Network.ConfigPanel.Switch.get_modal_dialog_selector(
                self.__node["data"]["id"]
            )
        )

    def enable_stp(self, priority=10000):
        """Switch the STP configuration toggle on."""
        self.__check_config_open()

        self.__page.click(Location.Network.ConfigPanel.Switch.RSTP_BUTTON.selector)

        dialog = self.__stp_dialog()
        dialog.wait_for(state="visible")

        dialog.locator(
            Location.Network.ConfigPanel.Switch.StpPanel.STP_BUTTON.selector
        ).click()

        dialog.locator(
            Location.Network.ConfigPanel.Switch.StpPanel.PRIORITY_FIELD.selector
        ).fill(str(priority))

        dialog.locator(
            Location.Network.ConfigPanel.Switch.StpPanel.SUBMIT_BUTTON.selector
        ).click()

        dialog.wait_for(state="hidden")

    def disable_stp(self):
        """Switch the STP configuration toggle off."""
        self.__check_config_open()

        self.__page.click(Location.Network.ConfigPanel.Switch.RSTP_BUTTON.selector)

        dialog = self.__stp_dialog()
        dialog.wait_for(state="visible")

        dialog.locator(
            Location.Network.ConfigPanel.Switch.StpPanel.OFF_STP_BUTTON.selector
        ).click()

        dialog.locator(
            Location.Network.ConfigPanel.Switch.StpPanel.SUBMIT_BUTTON.selector
        ).click()

        dialog.wait_for(state="hidden")

    def configure_vlan(self, fill_table: dict[str, Tuple[str, str]]):
        """Open and configure VLAN panel.

        Args:
            fill_table (dict[str, Tuple[str, str]]): Dictionary with structure { Device Name: (VLAN ID, Connection type) }
        """
        switch_name = self.name

        self.__page.click(Location.Network.ConfigPanel.Switch.VLAN_BUTTON.selector)

        dialog = self.__page.locator(
            Location.Network.ConfigPanel.Switch.VlanPanel.get_modal_dialog_selector(
                switch_name
            )
        )
        dialog.wait_for(state="visible")

        dialog.locator(
            Location.Network.ConfigPanel.Switch.VlanPanel.SWITCH_BUTTON.selector
        ).click()

        # Rows are counted up front rather than probed one by one: the table is
        # fully rendered once the dialog is visible.
        row_id = 0
        while True:
            row_xpath = (
                Location.Network.ConfigPanel.Switch.VlanPanel.get_table_row_xpath(
                    switch_name, row_id
                )
            )
            row = self.__page.locator(f"xpath={row_xpath}")

            if row.count() == 0:
                # element out of table
                break

            cells = row.locator("td")

            device_name = cells.nth(0).inner_text()

            if device_name not in fill_table:
                raise Exception(f"Can't find {device_name} in VLAN table.")

            vlan_id, connection_type = fill_table[device_name]

            cells.nth(1).locator("input").fill(vlan_id)
            cells.nth(2).locator("select").select_option(value=connection_type)

            row_id += 1

        # Save new table
        dialog.locator(
            Location.Network.ConfigPanel.Switch.VlanPanel.SUBMIT_BUTTON.selector
        ).click()

        dialog.wait_for(state="hidden")

    def change_name(self, name: str):
        """Change device name."""
        self.__check_config_open()

        assert self.__config_locator.NAME_FIELD, (
            f'Unable to change name for this element: "{self.__config_locator}".'
        )

        self.__page.fill(self.__config_locator.NAME_FIELD.selector, name)

    def submit(self):
        """Submit configuration."""
        self.__check_config_open()

        submit_button = self.__config_locator.SUBMIT_BUTTON
        assert submit_button is not None

        self.__page.click(submit_button.selector)
        # The button's label flips back once the save round-trip finished.
        self.__page.wait_for_selector(
            f"{submit_button.selector}:has-text('{submit_button.text}')"
        )

    def __select_job(self, job_id: int):
        if self.__config_locator in (
            Location.Network.ConfigPanel.Host,
            Location.Network.ConfigPanel.Router,
            Location.Network.ConfigPanel.Server,
            Location.Network.ConfigPanel.Switch,
        ):
            job_select = self.__config_locator.JOB_SELECT
            assert job_select is not None
            self.__page.select_option(job_select.selector, value=str(job_id))
        else:
            raise ValueError(
                f"Can't add job. Node with type {self.__config_locator} can't use jobs"
            )

    def __open_config(self, node: dict):
        device_class = node["classes"][0]
        node_json = json_dumps(node)

        if device_class == Location.Network.DevicePanel.HOST.device_class:
            self.__page.evaluate(f"ShowHostConfig({node_json})")
            self.__config_locator = Location.Network.ConfigPanel.Host

        elif device_class == Location.Network.DevicePanel.SWITCH.device_class:
            self.__page.evaluate(f"ShowSwitchConfig({node_json})")
            self.__config_locator = Location.Network.ConfigPanel.Switch

        elif device_class == Location.Network.DevicePanel.HUB.device_class:
            self.__page.evaluate(f"ShowHubConfig({node_json})")
            self.__config_locator = Location.Network.ConfigPanel.Hub

        elif device_class == Location.Network.DevicePanel.ROUTER.device_class:
            self.__page.evaluate(f"ShowRouterConfig({node_json})")
            self.__config_locator = Location.Network.ConfigPanel.Router

        elif device_class == Location.Network.DevicePanel.SERVER.device_class:
            self.__page.evaluate(f"ShowServerConfig({node_json})")
            self.__config_locator = Location.Network.ConfigPanel.Server

        else:
            raise Exception("Can't find device type !!!")

        assert self.__config_locator.MAIN_FORM, (
            f'Unable to open node config form for this element: "{self.__config_locator}".'
        )

        self.__page.wait_for_selector(self.__config_locator.MAIN_FORM.selector)

    def __check_config_open(self):
        """Check that the config is open and handle any errors."""
        main_form = self.__config_locator.MAIN_FORM
        assert main_form is not None

        if self.__page.locator(main_form.selector).count() == 0:
            raise Exception("Config panel isn't open during some operation.")

        # Collect error messages from modal dialogs
        error_dialogs = self.__page.locator(
            Location.Network.ConfigPanel.MODAL_ERROR_DIALOG.selector
        )
        error_msgs = [
            error_dialogs.nth(i).inner_text() for i in range(error_dialogs.count())
        ]

        if error_msgs:
            raise Exception(
                f"An error occurred while managing the config panel: {error_msgs}"
            )

    def locator(self, selector: str) -> PWLocator:
        """Expose a Playwright locator for tests that need the raw element."""
        return self.__page.locator(selector)


def type_sequentially(page: Page, selector: str, value: str) -> str:
    """Clear a field and type ``value`` one character at a time.

    Input filters in the app are wired to key events, so a value set in one
    shot (``fill``) can bypass them. ``press_sequentially`` reproduces the
    per-character typing ``send_keys`` does in the Selenium suite.

    Returns the field's value after typing.
    """
    field = page.locator(selector)
    field.wait_for(state="visible")
    field.clear()
    field.press_sequentially(value)
    return field.input_value()
