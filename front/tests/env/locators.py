from typing import Optional


class Locator:
    """Holds different types of locators for UI elements."""

    def __init__(self, selector=None, xpath=None, text=None, **kwargs):
        self.xpath = xpath
        self.selector = selector
        self.text = text

        for key, value in kwargs.items():
            setattr(self, key, value)


class Location:
    class NavigationButton:
        """Top buttons for navigating Miminet."""

        # "Мои сети"
        MY_NETWORKS_BUTTON = Locator("#my-networks-nav-item")
        # "Примеры сетей"
        NETWORK_EXAMPLES_BUTTON = Locator("#examples-nav-item")
        # "Тренажер"
        TRAINER_BUTTON = Locator("#trainer-nav-item")
        # "Учебные курсы"
        TRAINING_COURSES_BUTTON = Locator("#courses-nav-item")

    class MyNetworks:
        """User's networks page"""

        # "+ Новая сеть"
        NEW_NETWORK_BUTTON = Locator("#new-network-button")

        @staticmethod
        def get_network_button_xpath(id: int):
            """XPATH for specific network from home page.
            Args:
                id (int): Position of network in networks list. Starts from 0."""
            assert id >= 0, "Network button can't have index less than 0."
            return f"/html/body/section/div/div/div[{id+2}]"

    class Network:
        """Specific network page."""

        # Panel where you can place network devices and connect them
        MAIN_PANEL = Locator("#network_scheme")
        # Network device (or edge) configuration panel
        CONFIG_PANEL = Locator("#config_content")
        # Modal dialog for user warnings
        MODAL_DIALOG = Locator(xpath="/html/body/div[5]/div")
        # "Эмулировать"
        EMULATE_BUTTON = Locator("#NetworkEmulateButton", text="Эмулировать")
        # Pause animation button
        EMULATE_PLAYER_PAUSE_BUTTON = Locator("#NetworkPlayPauseButton")
        # Network title
        TITLE_LABEL = Locator("#network_title_head")

        class TopButton:
            """Data for identifying and locating top buttons of network interacting page."""

            # Network settings
            OPTIONS = Locator("#net-settings")
            # Copy network
            COPY = Locator("#copy-network")
            # Share network
            SHARE = Locator("#share-network")

        class ModalButton:
            # Copy
            GO_TO_EDITING = Locator(
                xpath='//*[@id="ModalCopy"]/div/div/div[2]/button[1]'
            )
            # Delete
            DELETE_MODAL_BUTTON = Locator("#networkDeleteButton")
            DELETE_SUBMIT_BUTTON = Locator("#networkDeleteSubmitButton")

        class DevicePanel:
            """Panel with network devices."""

            SWITCH = Locator("#l2_switch_device", device_class="l2_switch")
            HOST = Locator("#host_device", device_class="host")
            HUB = Locator("#l1_hub_device", device_class="l1_hub")
            ROUTER = Locator("#l3_router_device", device_class="l3_router")
            SERVER = Locator("#server_device", device_class="server")

        class ConfigPanel:
            """Elements in the configuration panel."""

            class CommonDevice:
                """Common type for ConfigPanel locators (add especially for mypy)."""

                MAIN_FORM: Optional[Locator] = None
                NAME_FIELD: Optional[Locator] = None
                DEFAULT_GATEWAY_FIELD: Optional[Locator] = None
                SUBMIT_BUTTON: Optional[Locator] = None
                JOB_SELECT: Optional[Locator] = None

            class Switch(CommonDevice):
                MAIN_FORM = Locator("#config_switch_main_form")
                NAME_FIELD = Locator("#switch_name")
                SUBMIT_BUTTON = Locator(
                    "#config_switch_main_form_submit_button", text="Сохранить"
                )

            class Host(CommonDevice):
                MAIN_FORM = Locator("#config_main_form")
                NAME_FIELD = Locator("#config_host_name")
                DEFAULT_GATEWAY_FIELD = Locator("#config_host_default_gw")
                SUBMIT_BUTTON = Locator(
                    "#config_host_main_form_submit_button", text="Сохранить"
                )
                JOB_SELECT = Locator("#config_host_job_select_field")

                class Job:
                    PING_FIELD = Locator("#config_host_ping_c_1_ip")
                    PING_OPTION_FIELD = Locator(
                        "#config_host_ping_with_options_options_input_field"
                    )
                    PING_OPTION_IP_FIELD = Locator(
                        "#config_host_ping_with_options_ip_input_field"
                    )
                    TCP_VOLUME_IN_BYTES_FIELD = Locator(
                        "#config_host_send_tcp_data_size_input_field"
                    )
                    TCP_IP_FIELD = Locator("#config_host_send_tcp_data_ip_input_field")
                    TCP_PORT_FIELD = Locator(
                        "#config_host_send_tcp_data_port_input_field"
                    )
                    UDP_VOLUME_IN_BYTES_FIELD = Locator(
                        "#config_host_send_udp_data_size_input_field"
                    )
                    UDP_IP_FIELD = Locator("#config_host_send_udp_data_ip_input_field")
                    UDP_PORT_FIELD = Locator(
                        "#config_host_send_udp_data_port_input_field"
                    )

            class Hub(CommonDevice):
                MAIN_FORM = Locator("#config_hub_main_form")
                NAME_FIELD = Locator("#config_hub_name")
                SUBMIT_BUTTON = Locator(
                    "#config_hub_main_form_submit_button",
                    text="Сохранить",
                )

            class Router(CommonDevice):
                MAIN_FORM = Locator("#config_main_form")
                NAME_FIELD = Locator("#config_router_name")
                DEFAULT_GATEWAY_FIELD = Locator("#config_router_default_gw")
                SUBMIT_BUTTON = Locator(
                    "#config_router_main_form_submit_button", text="Сохранить"
                )
                JOB_SELECT = Locator("#config_router_job_select_field")

                class Job:
                    NAT_LINK_SELECT = Locator(
                        "#config_router_add_nat_masquerade_iface_select_field"
                    )

            class Server(CommonDevice):
                MAIN_FORM = Locator("#config_main_form")
                NAME_FIELD = Locator("#config_server_name")
                DEFAULT_GATEWAY_FIELD = Locator("#config_server_default_gw")
                SUBMIT_BUTTON = Locator(
                    "#config_server_main_form_submit_button",
                    text="Сохранить",
                )
                JOB_SELECT = Locator("#config_server_job_select_field")

                class Job:
                    TCP_IP_FIELD = Locator(
                        "#config_server_start_tcp_server_ip_input_field"
                    )
                    TCP_PORT_FIELD = Locator(
                        "#config_server_start_tcp_server_port_input_field"
                    )
                    UDP_IP_FIELD = Locator(
                        "#config_server_start_udp_server_ip_input_field"
                    )
                    UDP_PORT_FIELD = Locator(
                        "#config_server_start_udp_server_port_input_field"
                    )

            # The only stable way for finding ip/subnet mask on page is using XPATHs

            @staticmethod
            def get_ip_field_xpath(id: int = 0):
                """XPATH for specific ip address from config panel.
                Args:
                    id (int): Position of link in links list. Starts from 0."""
                assert id >= 0, "IP field can't have index less than 0."
                return f"/html/body/main/section/div/div/div[3]/form/div[{4 + id * 2}]/input[1]"

            @staticmethod
            def get_mask_field_xpath(id: int = 0):
                """XPATH for specific subnet mask from config panel.
                Args:
                    id (int): Position of link in links list. Starts from 0."""
                assert id >= 0, "Subnet mask field can't have index less than 0."
                return f"/html/body/main/section/div/div/div[3]/form/div[{4 + id * 2}]/input[2]"


DEVICE_BUTTON_SELECTORS = [
    Location.Network.DevicePanel.SWITCH.selector,
    Location.Network.DevicePanel.HOST.selector,
    Location.Network.DevicePanel.HUB.selector,
    Location.Network.DevicePanel.ROUTER.selector,
    Location.Network.DevicePanel.SERVER.selector,
]
DEVICE_BUTTON_CLASSES = [
    Location.Network.DevicePanel.SWITCH.device_class,
    Location.Network.DevicePanel.HOST.device_class,
    Location.Network.DevicePanel.HUB.device_class,
    Location.Network.DevicePanel.ROUTER.device_class,
    Location.Network.DevicePanel.SERVER.device_class,
]
