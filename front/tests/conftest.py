import pytest
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import requests
from requests import Session


class testing_settings:
    domain = "localhost"
    chrome_driver_path = "/usr/local/bin/chromedriver"
    window_size = "1920,1080"
    auth_data = {"email": "selenium-email", "password": "password"}


MAIN_PAGE = f"http://{testing_settings.domain}"
HOME_PAGE = f"{MAIN_PAGE}/home"


@pytest.fixture(scope="class")
def chrome_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--window-size=%s" % testing_settings.window_size)
    chrome_options.add_argument("--no-sandbox")

    service = Service(testing_settings.chrome_driver_path)

    return Chrome(service=service, options=chrome_options)


@pytest.fixture(scope="class")
def requester():
    """Request session, used to send requests (GET, POST, etc...) and process their results

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
        data=testing_settings.auth_data,
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
                "domain": testing_settings.domain,
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
    yield chrome_driver

    chrome_driver.close()


@pytest.fixture(scope="class")
def new_empty_network(selenium: Chrome):
    """create 1 new network (same for all tests in this class)"""
    new_network_button_xpath = "/html/body/section/div/div/div[1]"
    options_button_xpath = "/html/body/nav/div/div[2]/a[3]/i"
    delete_network_button_xpath = "/html/body/div[1]/div/div/div[3]/button[1]"

    selenium.get(HOME_PAGE)
    selenium.find_element(By.XPATH, new_network_button_xpath).click()
    network_url = selenium.current_url

    yield network_url

    selenium.get(network_url)
    selenium.find_element(By.XPATH, options_button_xpath).click()
    selenium.find_element(By.XPATH, delete_network_button_xpath).click()
