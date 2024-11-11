from selenium.webdriver.common.by import By
from env.locators import (
    DEVICE_BUTTON_XPATHS,
    network_top_button,
    NETWORK_PANEL_XPATH,
    device_button,
    CONFIG_PANEL_XPATH,
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

    def __init__(self, selenium: MiminetTester):
        self.__selenium = selenium
        self.__build_empty_network()

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

        return ((x / 100) * width) - offset_x, ((y / 100) * width) - offset_x

    def __build_empty_network(self):
        """Create new network and clear it after use.

        Returns:
        (str) : Network URL
        """
        new_network_button_xpath = "/html/body/section/div/div/div[1]"

        self.__selenium.get(HOME_PAGE)
        self.__selenium.find_element(By.XPATH, new_network_button_xpath).click()

        self.__url = self.__selenium.current_url

    def scatter_devices(self):
        """Randomly add each network device to network."""
        panel = self.__selenium.find_element(By.XPATH, NETWORK_PANEL_XPATH)

        # calculate offset of coordinates inside panel
        for button_xpath in DEVICE_BUTTON_XPATHS:
            device = self.__selenium.find_element(By.XPATH, button_xpath)

            x, y = self.__calc_panel_offset(
                panel, random.randint(0, 100), random.randint(0, 100)
            )

            self.__selenium.drag_and_drop(device, panel, x, y)

    @property
    def nodes(self) -> dict:
        return self.__selenium.execute_script("return nodes")

    @property
    def edges(self) -> dict:
        return self.__selenium.execute_script("return edges")

    def open_node_config(self, device_node: dict):
        """Open configuration menu.

        Args:
            device_node (dict): Node for which the menu opens
        """
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
        edge_id = edge["data"]["id"]
        self.__selenium.execute_script(f"ShowEdgeConfig('{edge_id}')")
        WebDriverWait(self.__selenium, 5).until(
            EC.visibility_of_element_located((By.XPATH, CONFIG_PANEL_XPATH))
        )

    def add_node(self, device_button):
        """Add new device node

        Args:
            device_button (WebElement): Device button that can be moved
        """
        panel = self.__selenium.find_element(By.XPATH, NETWORK_PANEL_XPATH)

        x, y = self.__calc_panel_offset(
            panel, random.randint(0, 100), random.randint(0, 100)
        )

        self.__selenium.drag_and_drop(device_button, panel, x, y)

    def add_edge(self, source_node: dict, target_node: dict):
        source_id = str(source_node["data"]["id"])
        target_id = str(target_node["data"]["id"])

        self.__selenium.execute_script(f"AddEdge('{source_id}', '{target_id}')")
        self.__selenium.execute_script(f"DrawGraph()")
        self.__selenium.execute_script(f"PostNodesEdges()")

    def get_nodes_by_class(self, device_class: str) -> list[dict]:
        filtered_nodes = list(
            filter(lambda node: node["classes"][0] == device_class, self.nodes)
        )

        assert len(filtered_nodes) != 0, f"Can't find device node for {device_class}!!!"

        return filtered_nodes

    def delete(self):
        confirm_button_xpath = "/html/body/div[2]/div/div/div[2]/button[1]"

        self.__selenium.get(self.__url)

        self.__selenium.find_element(By.XPATH, network_top_button.options_xpath).click()

        self.__selenium.wait_and_click(By.XPATH, network_top_button.delete_xpath)
        self.__selenium.wait_and_click(By.XPATH, confirm_button_xpath)
