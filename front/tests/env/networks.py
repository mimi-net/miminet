from selenium.webdriver.common.by import By
from env.locators import Locator, CONFIG_PANEL_DEVICE_TYPE
from conftest import HOME_PAGE, MiminetTester
import random
from typing import Optional


class NodeType:
    """Node types for testing purposes."""

    Host = (By.CSS_SELECTOR, Locator.Network.DevicePanel.HOST["selector"])
    Switch = (By.CSS_SELECTOR, Locator.Network.DevicePanel.SWITCH["selector"])
    Router = (By.CSS_SELECTOR, Locator.Network.DevicePanel.ROUTER["selector"])
    Hub = (By.CSS_SELECTOR, Locator.Network.DevicePanel.HUB["selector"])
    Server = (By.CSS_SELECTOR, Locator.Network.DevicePanel.SERVER["selector"])


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
        assert (
            self.__selenium.current_url == self.__url
        ), "It is impossible to interact with the page without being on it"

    @property
    def url(self):
        """url to network page"""
        return self.__url

    @property
    def nodes(self) -> dict:
        """Current network nodes (may change during network usage)"""
        self.__check_page()
        return self.__selenium.execute_script("return nodes")

    @property
    def edges(self) -> dict:
        """Current network edges (may change during network usage)"""
        self.__check_page()
        return self.__selenium.execute_script("return edges")

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
        width, height = int(panel.rect["width"]), int(panel.rect["height"])
        target_x, target_y = int(panel.rect["x"]), int(panel.rect["y"])

        center_x, center_y = target_x + width / 2, target_y + height / 2
        offset_x, offset_y = center_x - target_x, center_y - target_y

        return ((x / 100) * width) - offset_x, ((y / 100) * height) - offset_y

    def __build_empty_network(self):
        """Create new network and clear it after use.

        Returns:
        (str) : Network URL
        """
        self.__selenium.get(HOME_PAGE)
        self.__selenium.find_element(
            By.CSS_SELECTOR, Locator.MyNetworks.NEW_NETWORK_BUTTON["selector"]
        ).click()

        self.__url = self.__selenium.current_url

    def scatter_devices(self):
        """Randomly add each network device to network."""
        self.__check_page()

        node_types = [
            NodeType.Host,
            NodeType.Switch,
            NodeType.Hub,
            NodeType.Router,
            NodeType.Server,
        ]
        random.shuffle(node_types)

        for type in node_types:
            self.add_node(type)

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
            By.CSS_SELECTOR, Locator.Network.CONFIG_PANEL["selector"]
        )

    def add_node(
        self,
        device_type: tuple[str, str],
        x: Optional[float] = None,
        y: Optional[float] = None,
    ):
        """Add new device node.

        Args:
            x (float): X-coordinate percentage within the panel (0-100).
            y (float): Y-coordinate percentage within the panel (0-100).
            device_button (WebElement): Device button that can be moved
        """
        self.__check_page()
        old_nodes_len = len(self.nodes)

        panel = self.__selenium.find_element(
            By.CSS_SELECTOR, Locator.Network.MAIN_PANEL["selector"]
        )

        x, y = random.uniform(0, 100) if x is None else x, (
            random.uniform(0, 100) if y is None else y
        )

        local_x, local_y = self.__calc_panel_offset(panel, x, y)

        device_button = self.__selenium.find_element(*device_type)

        self.__selenium.drag_and_drop(device_button, panel, local_x, local_y)
        self.__selenium.wait_for(lambda d: old_nodes_len < len(self.nodes))

    def add_edge(self, source_id: int, target_id: int):
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
            By.CSS_SELECTOR, Locator.Network.EMULATE_BUTTON["selector"]
        ).click()
        self.__selenium.wait_until_appear(
            By.CSS_SELECTOR, Locator.Network.EMULATE_PLAYER_PAUSE_BUTTON["selector"], 60
        )

        packets = self.__selenium.execute_script("return packets")

        return packets

    def delete(self):
        """Delete current network."""
        self.__check_page()

        self.__selenium.get(self.__url)

        self.__selenium.find_element(
            By.CSS_SELECTOR, Locator.Network.TopButton.OPTIONS["selector"]
        ).click()

        self.__selenium.wait_and_click(
            By.CSS_SELECTOR,
            Locator.Network.ModalButton.DELETE_MODAL_BUTTON["selector"],
        )
        self.__selenium.wait_and_click(
            By.CSS_SELECTOR,
            Locator.Network.ModalButton.DELETE_SUBMIT_BUTTON["selector"],
        )


class NodeConfig:
    """
    Represents a node configuration panel.
    You can easily add new jobs, links or set different values.
    """

    def __init__(self, selenium: MiminetTester, node: dict):
        self.__selenium = selenium
        # Locator with config elements
        self.__config_locator: CONFIG_PANEL_DEVICE_TYPE = (
            Locator.Network.ConfigPanel.Host
        )

        self.__open_config(node)

    @property
    def name(self):
        """Current name of the network device displayed in the configuration."""
        name = self.__selenium.find_element(
            By.CSS_SELECTOR, self.__config_locator.NAME_FIELD["selector"]
        ).get_attribute("value")

        return name

    @property
    def default_gw(self):
        """Current default gateway of the network device displayed in the configuration."""
        gw = self.__selenium.find_element(
            By.CSS_SELECTOR, self.__config_locator.DEFAULT_GATEWAY_FIELD["selector"]
        ).get_attribute("value")

        return gw

    def fill_link(self, ip: str, mask: int, link_id: int = 0):
        """Fill link (in config panel) with ip address and mask."""
        self.__check_config_open()

        self.__selenium.find_element(
            By.XPATH, Locator.Network.ConfigPanel.get_ip_field_xpath(link_id)
        ).send_keys(ip)
        self.__selenium.find_element(
            By.XPATH, Locator.Network.ConfigPanel.get_mask_field_xpath(link_id)
        ).send_keys(str(mask))

    def add_job(self, job_id: int, args: dict[str, str], by=By.CSS_SELECTOR):
        """Adds a job to the system using Selenium.

        Args:
            job_id: The ID of the job (currently unused in the implementation).
            args: A dictionary where keys represent locators for job fields and values
                  represent the corresponding values to be entered.
        """
        self.__check_config_open()

        if (
            self.__config_locator == Locator.Network.ConfigPanel.Host
            or self.__config_locator == Locator.Network.ConfigPanel.Switch
            or self.__config_locator == Locator.Network.ConfigPanel.Server
        ):
            self.__selenium.select_by_value(
                by, self.__config_locator.JOB_SELECT["selector"], job_id
            )
        else:
            raise ValueError(f"Node with type {self.__config_locator} can't use jobs")

        for job_field, job_value in args.items():
            self.__selenium.save_screenshot("1.png")
            try:
                self.__selenium.find_element(by, job_field).send_keys(job_value)
            except Exception as e:
                raise ValueError(
                    f"Can't add job. Job's field: {job_field}, value: {job_value}. Error message: {str(e)}"
                )

        # press "enter" to save job and remove job menu
        try:
            self.submit()
        except Exception:
            raise ValueError("Check that the entered data is correct.")

    def fill_default_gw(self, ip: str):
        """Fill default gateway with data."""
        self.__check_config_open()
        gw_field = self.__selenium.find_element(
            By.CSS_SELECTOR, self.__config_locator.DEFAULT_GATEWAY_FIELD["selector"]
        )
        gw_field.clear()
        gw_field.send_keys(ip)

    def change_name(self, name: str):
        """Change device name."""
        self.__check_config_open()
        name_field = self.__selenium.find_element(
            By.CSS_SELECTOR, self.__config_locator.NAME_FIELD["selector"]
        )
        name_field.clear()
        name_field.send_keys(name)

    def submit(self):
        """Submit configuration."""
        self.__check_config_open()
        self.__selenium.find_element(
            By.CSS_SELECTOR, self.__config_locator.SUBMIT_BUTTON["selector"]
        ).click()

        self.__selenium.wait_until_text(
            By.CSS_SELECTOR,
            self.__config_locator.SUBMIT_BUTTON["selector"],
            self.__config_locator.SUBMIT_BUTTON["text"],
            timeout=5,
        )

    def __open_config(self, node: dict):
        device_class = node["classes"][0]

        if device_class == Locator.Network.DevicePanel.HOST["device_class"]:
            self.__selenium.execute_script(f"ShowHostConfig({node})")
            self.__config_locator = Locator.Network.ConfigPanel.Host

        elif device_class == Locator.Network.DevicePanel.SWITCH["device_class"]:
            self.__selenium.execute_script(f"ShowSwitchConfig({node})")
            self.__config_locator = Locator.Network.ConfigPanel.Switch

        elif device_class == Locator.Network.DevicePanel.HUB["device_class"]:
            self.__selenium.execute_script(f"ShowHubConfig({node})")
            self.__config_locator = Locator.Network.ConfigPanel.Hub

        elif device_class == Locator.Network.DevicePanel.ROUTER["device_class"]:
            self.__selenium.execute_script(f"ShowRouterConfig({node})")
            self.__config_locator = Locator.Network.ConfigPanel.Router

        elif device_class == Locator.Network.DevicePanel.SERVER["device_class"]:
            self.__selenium.execute_script(f"ShowServerConfig({node})")
            self.__config_locator = Locator.Network.ConfigPanel.Server

        else:
            raise Exception("Can't find device type !!!")

        self.__selenium.wait_until_appear(
            By.CSS_SELECTOR, self.__config_locator.MAIN_FORM["selector"]
        )

    def __check_config_open(self):
        """Check that the config is open."""
        try:
            self.__selenium.find_element(
                By.CSS_SELECTOR, self.__config_locator.MAIN_FORM["selector"]
            )
        except Exception:
            raise Exception("Config panel isn't open.")


# ----- Compare functions -----


def compare_nodes(nodes_a, nodes_b) -> bool:
    """
    Compare nodes.

    :Returns:
        True if the nodes are equal.

    :Raises:
        AssertionError
    """
    if not nodes_a:
        raise ValueError("Nodes for comparison can't be empty.")
    if not nodes_b:
        raise ValueError("Nodes for comparison can't be empty.")
    if len(nodes_b) != len(nodes_a):
        raise ValueError(
            f"The number of nodes doesn't match. Expected {len(nodes_a)}, got {len(nodes_b)}."
        )

    for i, node_b in enumerate(nodes_b):
        node_a = nodes_a[i]

        if node_b["classes"] != node_a["classes"]:
            raise ValueError(
                f"Node {i}: Classes don't match. Expected {node_a['classes']}, got {node_b['classes']}."
            )

        if len(node_b["interface"]) != len(node_a["interface"]):
            raise ValueError(
                f"Node {i}: Number of interfaces doesn't match. Expected {len(node_a['interface'])}, got {len(node_b['interface'])}."
            )

        for iface_i, iface_b in enumerate(node_b["interface"]):
            my_iface_a = node_a["interface"][iface_i]

            if "ip" in my_iface_a.keys() and my_iface_a["ip"] != iface_b["ip"]:
                raise ValueError(
                    f"Node {i}, Interface {iface_i}: IP addresses don't match. Expected {my_iface_a['ip']}, got {iface_b['ip']}."
                )
            if (
                "netmask" in my_iface_a.keys()
                and my_iface_a["netmask"] != iface_b["netmask"]
            ):
                raise ValueError(
                    f"Node {i}, Interface {iface_i}: Netmasks don't match. Expected {my_iface_a['netmask']}, got {iface_b['netmask']}."
                )

        if node_b["data"] != node_a["data"]:
            raise ValueError(
                f"Node {i}: Data doesn't match. Expected {node_a['data']}, got {node_b['data']}."
            )

    return True


def compare_edges(edges_a, edges_b) -> bool:
    """Checks if the edges are equal.

    :Returns:
        True if the edges are equal.

    :Raises:
        AssertionError
    """
    if not edges_a:
        raise ValueError("Edges for comparison can't be empty.")
    if not edges_b:
        raise ValueError("Edges for comparison can't be empty.")

    if len(edges_b) != len(edges_a):
        raise ValueError(
            f"Number of edges mismatch: Expected {len(edges_a)}, got {len(edges_b)}."
        )

    for i, edge in enumerate(edges_b):
        my_edge = edges_a[i]

        try:
            edge_data = edge["data"]
            my_edge_data = my_edge["data"]

            if my_edge_data["source"] != edge_data["source"]:
                raise ValueError(
                    f"Edges sources don't match at index {i}: Expected {edge_data['source']}, got {my_edge_data['source']}."
                )
            if my_edge_data["target"] != edge_data["target"]:
                raise ValueError(
                    f"Edges targets don't match at index {i}: Expected {edge_data['target']}, got {my_edge_data['target']}."
                )

        except KeyError as e:
            raise ValueError(f"Missing key in edge data at index {i}: {e}")

    return True
