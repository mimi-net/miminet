class device_button:
    """Data for identifying and locating various network devices."""

    switch_xpath = "/html/body/main/section/div/div/div[1]/div/div[1]/img"
    switch_class = "l2_switch"

    host_xpath = "/html/body/main/section/div/div/div[1]/div/div[2]/img"
    host_class = "host"

    hub_xpath = "/html/body/main/section/div/div/div[1]/div/div[3]/img"
    hub_class = "l1_hub"

    router_xpath = "/html/body/main/section/div/div/div[1]/div/div[4]/img"
    router_class = "l3_router"

    server_xpath = "/html/body/main/section/div/div/div[1]/div/div[5]/img"
    server_class = "server"


class network_top_button:
    """Data for identifying and locating top buttons of network interacting page."""

    options_xpath = "/html/body/nav/div/div[2]/a[3]/i"
    delete_xpath = "/html/body/div[1]/div/div/div[3]/button[1]"
    copy_xpath = "/html/body/nav/div/div[2]/a[2]"


# Panel where you can place network devices and connect them
NETWORK_PANEL_XPATH = "/html/body/main/section/div/div/div[2]/div/div/canvas[2]"
# Network device configuration panel
CONFIG_PANEL_XPATH = "/html/body/main/section/div/div/div[3]"
# Network device name field
CONFIG_NAME_FIELD_XPATH = "/html/body/main/section/div/div/div[3]/form/div[1]/input"
# "Сохранить" button
CONFIG_CONFIRM_BUTTON_XPATH = "/html/body/main/section/div/div/div[3]/form/button"
# Network device IP address
CONFIG_IP_ADDRESS_FIELD_XPATH = (
    "/html/body/main/section/div/div/div[3]/form/div[4]/input[1]"
)
# Network device mask
CONFIG_MASK_FIELD_XPATH = "/html/body/main/section/div/div/div[3]/form/div[4]/input[2]"
# Select field with jobs
CONFIG_JOB_SELECT_XPATH = "/html/body/main/section/div/div/div[3]/form/div[2]/select"
# Job first field (e.g. ip-address for IP job)
JOB_FIELD_1_XPATH = "/html/body/main/section/div/div/div[3]/form/div[3]/input"

# "Мои сети" button
MY_NETWORK_BUTTON_XPATH = "/html/body/nav/div/div/li[3]/a"
# Modal dialog
MODAL_DIALOG_XPATH = "/html/body/div[5]/div"
# Copy button (inside network page)
NETWORK_COPY_BUTTON_XPATH = "/html/body/nav/div/div[2]/a[2]/i"
# "Перейти к редактированию" button (inside copy menu)
GO_TO_EDITING_BUTTON_XPATH = "/html/body/div[5]/div/div/div[2]/button[1]"
# Label with network name (inside network page)
NETWORK_NAME_LABEL_XPATH = "/html/body/nav/div/div[1]/a[3]"
# First button in networks menu
FIRST_NETWORK_BUTTON_XPATH = "/html/body/section/div/div/div[2]"
# "Эмулировать" button
EMULATE_BUTTON_XPATH = "/html/body/main/section/div/div/div[1]/div/div[6]/div[1]/button"
# Pause button in player
EMULATE_PLAYER_PAUSE_SELECTOR = "#NetworkPlayPauseButton"

CONFIG_CONFIRM_BUTTON_TEXT = "Сохранить"
EMULATE_BUTTON_TEXT = "Эмулировать"

DEVICE_BUTTON_XPATHS = [
    device_button.switch_xpath,
    device_button.host_xpath,
    device_button.hub_xpath,
    device_button.router_xpath,
    device_button.server_xpath,
]
DEVICE_BUTTON_CLASSES = [
    device_button.switch_class,
    device_button.host_class,
    device_button.hub_class,
    device_button.router_class,
    device_button.server_class,
]
