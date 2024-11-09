import pytest
from selenium.webdriver import Chrome
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import requests
from requests import Session
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class testing_setting:
    domain = "localhost"
    chrome_driver_path = "/usr/local/bin/chromedriver"
    window_size = "1920,1080"
    auth_data = {"email": "selenium-email", "password": "password"}


class device_button:
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


MAIN_PAGE = f"http://{testing_setting.domain}"
HOME_PAGE = f"{MAIN_PAGE}/home"
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


class Selenium(Chrome):
    """
    Extends the selenium.webdriver.Chrome class,
    adding new methods for convenient element interaction.
    """

    def wait_until_can_click(self, by: By, element: str, timeout=20):
        """
        Waits for the specified element to become clickable before clicking it.

        Args:
            by (By): The locator strategy (e.g., By.ID, By.XPATH).
            element (str): The element locator (e.g., "myElementId", "//button[text()='Click Me']").
            timeout (int): The maximum time in seconds to wait for the element to become clickable (default: 20).
        """
        WebDriverWait(self, timeout).until(
            EC.element_to_be_clickable((by, element))
        ).click()


@pytest.fixture(scope="class")
def chrome_driver():
    """Headless WebBrowser instance for testing (authorization here is not passed)."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--window-size=%s" % testing_setting.window_size)
    chrome_options.add_argument("--no-sandbox")

    service = Service(testing_setting.chrome_driver_path)

    tester = Selenium(service=service, options=chrome_options)

    yield tester

    tester.close()
    tester.quit()


@pytest.fixture(scope="class")
def requester():
    """Request session, used to send requests (GET, POST, etc...) and process their results.

    **[!]** Selenium is much slower than Requester! If you can test something by just making a request, without using Selenium, do it.
    """

    # Send a POST request to the http://XXXX.YY/auth/login.html
    # perform authorization with this and save cookies in session
    # use these cookies for other requests!

    session = requests.Session()

    response = session.get(MAIN_PAGE)

    if response.status_code != 200:
        raise Exception(
            "Miminet is not running or its address is incorrect: unable to get home page!"
        )

    response = session.post(
        f"{MAIN_PAGE}//auth/login.html",
        data=testing_setting.auth_data,
    )

    if response.status_code != 200:
        raise Exception("Unable to send authorization request!")

    yield session

    session.close()


@pytest.fixture(scope="class")
def selenium(chrome_driver: Chrome, requester: Session):
    chrome_driver.get(MAIN_PAGE)
    cookies = requester.cookies

    for cookie in cookies:
        if cookie.name and cookie.value and cookie.expires:
            selenium_cookie = {
                "domain": testing_setting.domain,
                "expiry": cookie.expires,
                "httpOnly": False,
                "name": cookie.name,
                "path": "/",
                "sameSite": "Lax",
                "secure": False,
                "value": cookie.value,
            }
            chrome_driver.add_cookie(selenium_cookie)

    # return configured chrome driver
    return chrome_driver
