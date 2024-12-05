from selenium.webdriver.common.by import By
from env.locators import Locator, DEVICE_BUTTON_SELECTORS
from conftest import HOME_PAGE, MiminetTester
import random
from typing import Optional


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
            By.CSS_SELECTOR, Locator.MyNetworks.NEW_NETWORK_BUTTON['selector']
        ).click()

        self.__url = self.__selenium.current_url

    def scatter_devices(self):
        """Randomly add each network device to network."""
        self.__check_page()

        for button_id in DEVICE_BUTTON_SELECTORS:
            device = self.__selenium.find_element(By.CSS_SELECTOR, button_id)
            self.add_node(device)

    def open_node_config(self, device_node: dict):
        """Open configuration menu.

        Args:
            device_node (dict): Node for which the menu opens
        """
        self.__check_page()
        device_class = device_node["classes"][0]

        if device_class == Locator.Network.DevicePanel.HOST["device_class"]:
            self.__selenium.execute_script(f"ShowHostConfig({device_node})")
        elif device_class == Locator.Network.DevicePanel.SWITCH["device_class"]:
            self.__selenium.execute_script(f"ShowSwitchConfig({device_node})")
        elif device_class == Locator.Network.DevicePanel.HUB["device_class"]:
            self.__selenium.execute_script(f"ShowHubConfig({device_node})")
        elif device_class == Locator.Network.DevicePanel.ROUTER["device_class"]:
            self.__selenium.execute_script(f"ShowRouterConfig({device_node})")
        elif device_class == Locator.Network.DevicePanel.SERVER["device_class"]:
            self.__selenium.execute_script(f"ShowServerConfig({device_node})")
        else:
            raise Exception("Can't find device type !!!")

        self.__selenium.wait_until_appear(By.CSS_SELECTOR, Locator.Network.CONFIG_PANEL['selector'])

    def open_edge_config(self, edge: dict):
        """Open configuration menu.

        Args:
            edge (dict): Edge for which the menu opens
        """
        self.__check_page()
        edge_id = edge["data"]["id"]
        self.__selenium.execute_script(f"ShowEdgeConfig('{edge_id}')")

        self.__selenium.wait_until_appear(By.CSS_SELECTOR, Locator.Network.CONFIG_PANEL['selector'])

    def submit_config(self):
        """Close configuration menu."""
        self.__check_page()
        self.__selenium.find_element(
            By.XPATH, Locator.Network.ConfigPanel.SUBMIT_BUTTON["xpath"]
        ).click()

        self.__selenium.wait_until_text(
            By.XPATH,
            Locator.Network.ConfigPanel.SUBMIT_BUTTON["xpath"],
            Locator.Network.ConfigPanel.SUBMIT_BUTTON["text"],
            timeout=5,
        )

    def add_node(
        self, device_button, x: Optional[float] = None, y: Optional[float] = None
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
            By.CSS_SELECTOR, Locator.Network.MAIN_PANEL['selector']
        )

        x, y = random.uniform(0, 100) if x is None else x, (
            random.uniform(0, 100) if y is None else y
        )

        local_x, local_y = self.__calc_panel_offset(panel, x, y)

        self.__selenium.drag_and_drop(device_button, panel, local_x, local_y)
        self.__selenium.wait_for(lambda d: old_nodes_len < len(self.nodes))

    def add_edge(self, source_node: dict, target_node: dict):
        self.__check_page()
        old_edges_len = len(self.edges)

        source_id = str(source_node["data"]['id'])
        target_id = str(target_node["data"]['id'])

        self.__selenium.execute_script(f"AddEdge('{source_id}', '{target_id}')")
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

    def fill_link(self, ip: str, mask: int, node, link_id: int = 0):
        """Fill link (in config panel) with ip address and mask."""
        self.__check_page()

        self.open_node_config(node)
        self.__selenium.find_element(By.XPATH, Locator.Network.ConfigPanel.get_ip_field_xpath(link_id)).send_keys(ip)
        self.__selenium.find_element(By.XPATH, Locator.Network.ConfigPanel.get_mask_field_xpath(link_id)).send_keys(mask)

        self.submit_config()

    def run_emulation(self) -> dict:
        """Run miminet emulation.

        [!] This function doesn't work in CI for unknown reasons :(.

        :Return: Emulation packets."""
        self.__check_page()
        self.__selenium.find_element(
            By.CSS_SELECTOR, Locator.Network.EMULATE_BUTTON['selector']
        ).click()
        self.__selenium.wait_until_appear(
            By.CSS_SELECTOR, Locator.Network.EMULATE_PLAYER_PAUSE_BUTTON['selector'], 60
        )

        packets = self.__selenium.execute_script("return packets")

        return packets

    def delete(self):
        self.__check_page()

        self.__selenium.get(self.__url)

        self.__selenium.find_element(
            By.CSS_SELECTOR, Locator.Network.TopButton.OPTIONS['selector']
        ).click()

        self.__selenium.wait_and_click(
            By.CSS_SELECTOR, Locator.Network.TopButton.ModalButton.DELETE_MODAL_BUTTON['selector']
        )
        self.__selenium.wait_and_click(
            By.CSS_SELECTOR, Locator.Network.TopButton.ModalButton.DELETE_SUBMIT_BUTTON['selector']
        )

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

    for i, node in enumerate(nodes_b):
        my_node = nodes_a[i]

        if node["classes"] != my_node["classes"]:
            raise ValueError(
                f"Node {i}: Classes don't match. Expected {my_node['classes']}, got {node['classes']}."
            )

        if len(node["interface"]) != len(my_node["interface"]):
            raise ValueError(
                f"Node {i}: Number of interfaces doesn't match. Expected {len(my_node['interface'])}, got {len(node['interface'])}."
            )

        for iface_i, iface in enumerate(node["interface"]):
            my_iface = my_node["interface"][iface_i]

            if my_iface["ip"] != iface["ip"]:
                raise ValueError(
                    f"Node {i}, Interface {iface_i}: IP addresses don't match. Expected {my_iface['ip']}, got {iface['ip']}."
                )
            if my_iface["netmask"] != iface["netmask"]:
                raise ValueError(
                    f"Node {i}, Interface {iface_i}: Netmasks don't match. Expected {my_iface['netmask']}, got {iface['netmask']}."
                )

        if node["data"] != my_node["data"]:
            raise ValueError(
                f"Node {i}: Data doesn't match. Expected {my_node['data']}, got {node['data']}."
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