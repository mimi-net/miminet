import pytest
from selenium import webdriver
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import requests
from requests import Session


class testing_settings:
    domain = "localhost"
    chrome_driver_path = "/usr/local/bin/chromedriver"
    window_size = "1920,1080"
    auth_data = {"email": "selenium-email", "password": "password"}
    miminet_address = f"http://{domain}"


@pytest.fixture(scope="class")
def chrome_driver():
    # Set path Selenium
    CHROMEDRIVER_PATH = testing_settings.chrome_driver_path
    WINDOW_SIZE = testing_settings.window_size

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--window-size=%s" % WINDOW_SIZE)
    chrome_options.add_argument("--no-sandbox")

    service = Service(CHROMEDRIVER_PATH)

    return Chrome(service=service, options=chrome_options)


@pytest.fixture(scope="class")
def testing_session():
    # Send a POST request to the http://XXXX.YY/auth/login.html
    # perform authorization with this and save cookies in session
    # use these cookies for other requests!

    session = requests.Session()

    response = session.get(testing_settings.miminet_address)

    if response.status_code != 200:
        raise Exception(
            "Miminet is not running or its address is incorrect: unable to get home page!"
        )

    response = session.post(
        f"{testing_settings.miminet_address}//auth/login.html",
        data=testing_settings.auth_data,
    )

    if response.status_code != 200:
        raise Exception("Unable to send authorization request!")

    yield session

    session.close()


@pytest.fixture(scope="class")
def selenium(chrome_driver, testing_session):
    chrome_driver.get(testing_settings.miminet_address)
    cookies = testing_session.cookies

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
