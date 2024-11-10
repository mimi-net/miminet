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
CONFIG_PANEL_XPATH = "/html/body/main/section/div/div/div[3]"
CONFIG_NAME_FIELD_XPATH = "/html/body/main/section/div/div/div[3]/form/div[1]/input"
CONFIG_CONFIRM_BUTTON_XPATH = "/html/body/main/section/div/div/div[3]/form/button"
MY_NETWORK_BUTTON_XPATH = "/html/body/nav/div/div/li[3]/a"
NETWORK_NAME_LABEL_XPATH = "/html/body/nav/div/div[1]/a[3]"
FIRST_NETWORK_BUTTON_XPATH = "/html/body/section/div/div/div[2]"


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
