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


@pytest.fixture(scope="session")
def main_page():
    return f"http://{testing_settings.domain}"


@pytest.fixture(scope="class")
def chrome_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--window-size=%s" % testing_settings.window_size)
    chrome_options.add_argument("--no-sandbox")

    service = Service(testing_settings.chrome_driver_path)

    return Chrome(service=service, options=chrome_options)


@pytest.fixture(scope="class")
def requester(main_page: str):
    """Request session, used to send requests (GET, POST, etc...) and process their results

    **[!]** Selenium is much slower than Requester! If you can test something by just making a request, without using Selenium, do it.
    """

    # Send a POST request to the http://XXXX.YY/auth/login.html
    # perform authorization with this and save cookies in session
    # use these cookies for other requests!

    session = requests.Session()

    response = session.get(main_page)

    if response.status_code != 200:
        raise Exception(
            "Miminet is not running or its address is incorrect: unable to get home page!"
        )

    response = session.post(
        f"{main_page}//auth/login.html",
        data=testing_settings.auth_data,
    )

    if response.status_code != 200:
        raise Exception("Unable to send authorization request!")

    yield session

    session.close()


@pytest.fixture(scope="class")
def selenium(chrome_driver: Chrome, requester: Session, main_page: str):
    chrome_driver.get(main_page)
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
