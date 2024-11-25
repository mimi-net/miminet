from selenium.webdriver.common.by import By
from env.locators import (
    DEVICE_BUTTON_XPATHS,
    network_top_button,
    NETWORK_PANEL_XPATH,
    device_button,
    CONFIG_PANEL_XPATH,
    NEW_NETWORK_BUTTON_XPATH,
    EMULATE_BUTTON_XPATH,
    EMULATE_PLAYER_PAUSE_SELECTOR,
)
from conftest import HOME_PAGE, MiminetTester
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import random


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
        return self.__url

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
        self.__selenium.find_element(By.XPATH, NEW_NETWORK_BUTTON_XPATH).click()

        self.__url = self.__selenium.current_url

    def scatter_devices(self):
        """Randomly add each network device to network."""
        self.__check_page()

        for button_xpath in DEVICE_BUTTON_XPATHS:
            device = self.__selenium.find_element(By.XPATH, button_xpath)
            self.add_node(device)

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

    def open_node_config(self, device_node: dict):
        """Open configuration menu.

        Args:
            device_node (dict): Node for which the menu opens
        """
        self.__check_page()
        device_class = device_node["classes"][0]

        if device_class == device_button.host_class:
            self.__selenium.execute_script(f"ShowHostConfig({device_node})")
        elif device_class == device_button.switch_class:
            self.__selenium.execute_script(f"ShowSwitchConfig({device_node})")
        elif device_class == device_button.hub_class:
            self.__selenium.execute_script(f"ShowHubConfig({device_node})")
        elif device_class == device_button.router_class:
            self.__selenium.execute_script(f"ShowRouterConfig({device_node})")
        elif device_class == device_button.server_class:
            self.__selenium.execute_script(f"ShowServerConfig({device_node})")
        else:
            raise Exception("Can't find device type !!!")

        WebDriverWait(self.__selenium, 5).until(
            EC.visibility_of_element_located((By.XPATH, CONFIG_PANEL_XPATH))
        )

    def open_edge_config(self, edge: dict):
        """Open configuration menu.

        Args:
            edge (dict): Edge for which the menu opens
        """
        self.__check_page()
        edge_id = edge["data"]["id"]
        self.__selenium.execute_script(f"ShowEdgeConfig('{edge_id}')")

        self.__selenium.wait_until_appear(By.XPATH, CONFIG_PANEL_XPATH)

    def add_node(self, device_button):
        """Add new device node

        Args:
            device_button (WebElement): Device button that can be moved
        """
        self.__check_page()
        old_nodes_len = len(self.nodes)

        panel = self.__selenium.find_element(By.XPATH, NETWORK_PANEL_XPATH)

        x, y = self.__calc_panel_offset(
            panel, random.randint(0, 100), random.randint(0, 100)
        )

        self.__selenium.drag_and_drop(device_button, panel, x, y)
        self.__selenium.wait_for(old_nodes_len < len(self.nodes))

    def add_edge(self, source_node: dict, target_node: dict):
        self.__check_page()
        old_edges_len = len(self.edges)

        source_id = str(source_node["data"]["id"])
        target_id = str(target_node["data"]["id"])

        self.__selenium.execute_script(f"AddEdge('{source_id}', '{target_id}')")
        self.__selenium.execute_script("DrawGraph()")
        self.__selenium.execute_script("PostNodesEdges()")

        self.__selenium.wait_for(old_edges_len < len(self.edges))

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
        self.__selenium.find_element(By.XPATH, EMULATE_BUTTON_XPATH).click()
        self.__selenium.wait_until_appear(
            By.CSS_SELECTOR, EMULATE_PLAYER_PAUSE_SELECTOR, 60
        )

        packets = self.__selenium.execute_script("return packets")

        return packets

    def are_nodes_equal(self, nodes: dict) -> bool:
        self.__check_page()

        my_nodes = self.nodes

        assert my_nodes, "The current network has no nodes."
        assert nodes, "Nodes for comparison can't be empty."

        assert len(nodes) == len(my_nodes), "The number of nodes doesn't match."

        for i, node in enumerate(nodes):
            my_node = my_nodes[i]

            assert node["classes"] == my_node["classes"], f"Node {node} classes don't match."

            assert len(node["interface"]) == len(
                my_node["interface"]
            ), "Number of interfaces doesn't match"

            for iface_i, iface in enumerate(node['interface']):
                my_iface = my_node['interface'][iface_i]

                assert my_iface['ip'] == iface['ip'], f"Node {node} iface's ip don't match"
                assert my_iface['netmask'] == iface['netmask'], f"Node {node} iface's netmask don't match"

            assert node["data"] == my_node["data"], "Nodes data don't match."
        
        return True

    def are_edges_equal(self, b: dict) -> bool:
        self.__check_page()

        a = self.edges

        assert a, "The current network has no edges."
        assert b, "Edges for comparison can't be empty."

        assert len(b) == len(a), "The number of nodes doesn't match."

        for i, edge in enumerate(b):
            my_edge = a[i]

            edge_data = edge['data']
            my_edge_data = my_edge['data']

            assert (
                my_edge_data["source"] == edge_data["source"]
            ), "Edges sources don't match"
            assert (
                my_edge_data["target"] == edge_data["target"]
            ), "Edges targets don't match"

        return True

    def delete(self):
        self.__check_page()

        confirm_button_xpath = "/html/body/div[2]/div/div/div[2]/button[1]"

        self.__selenium.get(self.__url)

        self.__selenium.find_element(By.XPATH, network_top_button.options_xpath).click()

        self.__selenium.wait_and_click(By.XPATH, network_top_button.delete_xpath)
        self.__selenium.wait_and_click(By.XPATH, confirm_button_xpath)
