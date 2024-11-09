from environment_setup import environment_setting

MAIN_PAGE = f"http://{environment_setting.domain}"
HOME_PAGE = f"{MAIN_PAGE}/home"


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
