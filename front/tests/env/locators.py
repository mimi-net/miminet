class PageLocator:
    class NavigationTopButton:
        """Top buttons for navigating Miminet."""

        MY_NETWORKS_BUTTON = {"ID": "#my-networks-nav-item"}
        NETWORK_EXAMPLES_BUTTON = {"ID": "#examples-nav-item"}
        TRAINER_BUTTON = {"ID": "#trainer-nav-item"}
        TRAINING_COURSES_BUTTON = {"ID": "#courses-nav-item"}

    class MyNetworks:
        """User's networks page"""

        NEW_NETWORK_BUTTON = {"ID": "#new-network-button"}

        def get_network_button_xpath(id: int):
            """XPATH for specific network from home page.
            Args:
                id (int): Position of network in networks list. Starts from 0."""
            assert id >= 0, "Network button can't have index less than 0."
            return f"/html/body/section/div/div/div[{id+2}]"

    class Network:
        """Specific network page."""

        # Panel where you can place network devices and connect them
        MAIN_PANEL = {"ID": "#network_scheme"}
        # Network device (or edge) configuration panel
        CONFIG_PANEL = {"ID": "#config_content"}
        # Modal dialog for user warnings
        MODAL_DIALOG = {"CLASS": "modal-dialog"}
        # Button for emulation starting
        EMULATE_BUTTON = {"ID": "#NetworkEmulateButton", "TEXT": "Эмулировать"}
        # Pause animation button
        EMULATE_PLAYER_PAUSE_BUTTON = {"ID": "#NetworkPlayPauseButton"}
        # Network title
        TITLE_LABEL = {"ID": "#network_title_head"}

        class TopButton:
            """Data for identifying and locating top buttons of network interacting page."""

            OPTIONS = {"XPATH": "/html/body/nav/div/div[2]/a[3]"}
            DELETE = {"XPATH": "/html/body/div[1]/div/div/div[3]/button[1]"}
            COPY = {"XPATH": "/html/body/nav/div/div[2]/a[2]"}

            class ModalButton:
                # Copy
                GO_TO_EDITING = {
                    "XPATH": '//*[@id="ModalCopy"]/div/div/div[2]/button[1]'
                }
                # Delete
                DELETE_MODAL_BUTTON = {"ID": "#networkDeleteButton"}
                DELETE_SUBMIT_BUTTON = {"ID": "#networkDeleteSubmitButton"}

        class DevicePanel:
            """Panel with network devices."""

            SWITCH = {"ID": "#l2_switch", "DEVICE_CLASS": "l2_switch"}
            HOST = {"ID": "#host", "DEVICE_CLASS": "host"}
            HUB = {"ID": "#l1_hub", "DEVICE_CLASS": "l1_hub"}
            ROUTER = {"ID": "#l3_router", "DEVICE_CLASS": "l3_router"}
            SERVER = {"ID": "#server", "DEVICE_CLASS": "server"}

        class ConfigPanel:
            """Elements in the configuration panel."""

            # Network device name field
            CONFIG_NAME_FIELD = {"ID": "#config_host_name"}
            DEFAULT_GATEWAY_FIELD = {"ID": "#config_host_default_gw"}
            SUBMIT_BUTTON = {
                "ID": "#config_host_main_form_submit_button",
                "TEXT": "Сохранить",
            }
            JOB_SELECT = {"ID": "#config_host_job_select_field"}

            def get_ip_field_xpath(id: int = 0):
                """XPATH for specific ip address from config panel.
                Args:
                    id (int): Position of link in links list. Starts from 0."""
                assert id >= 0, "IP field can't have index less than 0."
                return f"/html/body/main/section/div/div/div[3]/form/div[4]/input[{1 + id * 2}]"

            def get_mask_field_xpath(id: int = 0):
                """XPATH for specific subnet mask from config panel.
                Args:
                    id (int): Position of link in links list. Starts from 0."""
                assert id >= 0, "Subnet mask field can't have index less than 0."
                return f"/html/body/main/section/div/div/div[3]/form/div[4]/input[{2 + id*2}]"

            class Job:
                """Jobs fields."""

                PING_FIELD = {"ID": "#config_host_ping_c_1_ip"}
                PING_OPTION_FIELD = {
                    "ID": "#config_host_ping_with_options_options_input_field"
                }
                PING_OPTION_IP_FIELD = {
                    "ID": "#config_host_ping_with_options_ip_input_field"
                }


DEVICE_BUTTON_IDS = [
    PageLocator.Network.DevicePanel.SWITCH["id"],
    PageLocator.Network.DevicePanel.HOST["id"],
    PageLocator.Network.DevicePanel.HUB["id"],
    PageLocator.Network.DevicePanel.ROUTER["id"],
    PageLocator.Network.DevicePanel.SERVER["id"],
]
DEVICE_BUTTON_CLASSES = [
    PageLocator.Network.DevicePanel.SWITCH["DEVICE_CLASS"],
    PageLocator.Network.DevicePanel.HOST["DEVICE_CLASS"],
    PageLocator.Network.DevicePanel.HUB["DEVICE_CLASS"],
    PageLocator.Network.DevicePanel.ROUTER["DEVICE_CLASS"],
    PageLocator.Network.DevicePanel.SERVER["DEVICE_CLASS"],
]
