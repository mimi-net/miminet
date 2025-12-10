import pytest
import requests
import os
import sys
from typing import Generator
from requests import Session
from contextlib import contextmanager
from unittest.mock import MagicMock
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains


class testing_setting:
    """Configuration settings for testing environment."""

    nginx_docker_ip = "172.18.0.2"  # nginx IP inside miminet docker network
    selenium_hub_url = (
        "http://localhost:4444/wd/hub"  # route for sending selenium commands
    )
    window_size = "1920,1080"
    auth_data = {
        "email": "selenium",
        "password": "password",
    }  # this data should be inserted into the database, selenium uses it for authentication


MAIN_PAGE = f"http://{testing_setting.nginx_docker_ip}"
HOME_PAGE = f"{MAIN_PAGE}/home"
LOGIN_PAGE = f"{MAIN_PAGE}//auth/login.html"


class MiminetTester(WebDriver):
    """
    Extends standard selenium class,
    adding new methods for convenient element interaction.
    """

    def wait_and_click(self, by: str, element: str, timeout=20):
        """
        Waits for the specified element to become clickable before clicking it.

        Args:
            by (By): The locator strategy (e.g., By.ID, By.XPATH).
            element (str): The element locator (e.g., "myElementId", "//button[text()='Click Me']").
            timeout (int): The maximum time in seconds to wait (default: 20).
        """
        WebDriverWait(self, timeout).until(
            EC.element_to_be_clickable((by, element))
        ).click()

    def drag_and_drop(self, source: WebElement, target: WebElement, x: int, y: int):
        """Performs a drag-and-drop action from a source element to a target element.

        Args:
            source (WebElement): The source element to be dragged.
            target (WebElement): The target element to drop the source element onto.
            x (int): The x-offset to move to.
            y (int): The y-offset to move to.
        """
        actions_chain = ActionChains(self)

        actions_chain.click_and_hold(source)
        actions_chain.move_to_element_with_offset(target, x, y)
        actions_chain.release()
        actions_chain.perform()

    def exist_element(self, by: str, element: str):
        """
        Check if an element exists on the page.

        Args:
            by (str): The locator strategy (e.g., By.ID, By.XPATH).
            element (str): The element locator (e.g., "myElementId", "//button[text()='Click Me']").
        """

        return len(self.find_elements(by, element)) > 0

    def wait_until_appear(self, by: str, element: str, timeout=20):
        """
        Waits until the specified element is present in the page's DOM and becomes visible.

        Args:
            by (str): The locator strategy (e.g., By.ID, By.XPATH).
            element (str): The element locator (e.g., "myElementId", "//button[text()='Click Me']").
            timeout (int): The maximum time in seconds to wait (default: 20).
        """
        WebDriverWait(self, timeout).until(
            EC.visibility_of_element_located((by, element))
        )

    def wait_until_disappear(self, by: str, element: str, timeout=20):
        """
        Waits until the specified element disappears from the page's DOM and becomes invisible.

        Args:
            by (str): The locator strategy (e.g., By.ID, By.XPATH).
            element (str): The element locator (e.g., "myElementId", "//button[text()='Click Me']").
            timeout (int): The maximum time in seconds to wait (default: 20).
        """
        WebDriverWait(self, timeout).until(
            EC.invisibility_of_element_located((by, element))
        )

    def wait_until_text(self, by: str, element: str, text: str, timeout=20):
        """
        Waits until text appears in the element.

        Args:
            by (str): The locator strategy (e.g., By.ID, By.XPATH).
            element (str): The element locator (e.g., "myElementId", "//button[text()='Click Me']").
            timeout (int): The maximum time in seconds to wait (default: 20).
        """
        WebDriverWait(self, timeout).until(
            EC.text_to_be_present_in_element((by, element), text)
        )

    def wait_for(self, condition, timeout=20):
        """Waits for a given condition to be true.

        Args:
            condition: A function that returns True when the condition is met. This function have WebDriver instance as its only argument.
            timeout (int): The maximum time in seconds to wait (default: 20).
        """
        WebDriverWait(self, timeout=timeout).until(condition)

    @contextmanager
    def run_in_modal_context(
        self, by: str, element: str
    ) -> Generator[WebElement, None, None]:
        """
        Allow to do actions in the context of modal window.
        """
        try:
            self.wait_until_appear(by, element, timeout=5)

            yield self.find_element(by, element)
        except TimeoutException:
            raise Exception(f"Modal dialog {element} wasn't opened.")
        finally:
            # TODO change it to wait_until_disappear when modal dialog will be fixed
            self.wait_for(
                lambda driver: not driver.find_element(by, element).is_displayed(),
                timeout=5,
            )

    def select_by_value(self, by: str, element: str, value: str):
        """Selects an option in a select element by its value.

        Args:
            by (str): The locator strategy (e.g., By.ID, By.XPATH).
            element (str): The element locator (e.g., "myElementId", "//button[text()='Click Me']").
            value: The value attribute of the option to select.
        """
        select = Select(self.find_element(by, element))
        select.select_by_value(value)

    def get_logs(self, logs_filter=None):
        """
        Retrieve browser logs with an optional filter.

        Args:
            logs_filter (function, optional): A function that takes a log entry as input
                                            and returns True if the entry should be included.
                                            Defaults to None, meaning all logs are returned.
        Returns:
            list: list with the filtered log entries.
        """
        logs = self.get_log("browser")
        return list(filter(logs_filter, logs)) if logs_filter else list(logs)

    def get_console_messages(self):
        """
        Retrieve browser console logs (console.log()). This can be used in debug purposes.
        Returns:
            iterator: list with the log messages.
        """
        return map(
            lambda log: log["message"],
            self.get_logs(
                lambda log: log["source"] == "console-api" and log["level"] == "INFO"
            ),
        )


@pytest.fixture(scope="session")
def chrome_driver():
    """Headless WebBrowser instance for testing (authorization here is not passed)."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--window-size=%s" % testing_setting.window_size)
    chrome_options.add_argument("--no-sandbox")

    chrome_options.set_capability(
        "goog:loggingPrefs", {"browser": "ALL"}
    )  # Capture console logs

    tester = MiminetTester(testing_setting.selenium_hub_url, options=chrome_options)

    yield tester

    tester.close()
    tester.quit()


@pytest.fixture(scope="session")
def requester():
    """Request session, used to send requests (GET, POST, etc...) and process their results.

    **[!]** Selenium is much slower than Requester! If you can test something by just making a request, without using Selenium, do it.
    """

    # Send a POST request to the http://XXXX.YY/auth/login.html
    # perform authorization with this and save cookies in session
    # use these cookies for other requests!

    session = requests.Session()

    response = session.get(MAIN_PAGE)

    assert (
        response.status_code == 200
    ), "Miminet is not running or its address is incorrect: unable to get home page!"

    response = session.post(
        f"{MAIN_PAGE}//auth/login.html",
        data=testing_setting.auth_data,
    )

    assert response.status_code == 200, "Unable to send authorization request!"
    assert response.url != LOGIN_PAGE, "Failed to login using the specified data"

    yield session

    session.close()


@pytest.fixture(scope="session")
def selenium(chrome_driver: MiminetTester, requester: Session):
    chrome_driver.get(MAIN_PAGE)
    cookies = requester.cookies

    # gift cookies to selenium
    for cookie in cookies:
        if cookie.name and cookie.value and cookie.expires:
            selenium_cookie = {
                "domain": testing_setting.nginx_docker_ip,
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


# --- Unit Test Fixtures ---

# Add src to path so tests can import app and miminet_model
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))


@pytest.fixture
def mock_env_dev(monkeypatch):
    """Sets environment variables for DEV mode."""
    monkeypatch.setenv("MODE", "dev")
    monkeypatch.setenv("POSTGRES_HOST", "localhost")
    monkeypatch.setenv("POSTGRES_DEFAULT_USER", "user")
    monkeypatch.setenv("POSTGRES_DEFAULT_PASSWORD", "pass")
    monkeypatch.setenv("POSTGRES_DATABASE_NAME", "miminet_dev")
    monkeypatch.delenv("YANDEX_POSTGRES_HOST", raising=False)


@pytest.fixture
def mock_env_prod(monkeypatch):
    """Sets environment variables for PROD mode."""
    monkeypatch.setenv("MODE", "prod")
    monkeypatch.setenv("YANDEX_POSTGRES_HOST", "rc1a-test.mdb.yandexcloud.net")
    monkeypatch.setenv("YANDEX_POSTGRES_PORT", "6432")
    monkeypatch.setenv("YANDEX_POSTGRES_USER", "prod_user")
    monkeypatch.setenv("YANDEX_POSTGRES_PASSWORD", "prod_pass")
    monkeypatch.setenv("YANDEX_POSTGRES_DB", "miminet_prod")
    monkeypatch.setenv("YANDEX_POSTGRES_SSLMODE", "verify-full")
    monkeypatch.setenv("YANDEX_POSTGRES_SSLROOTCERT", "/tmp/root.crt")


@pytest.fixture
def mock_psycopg2(mocker):
    """Mocks psycopg2 to capture connection attempts."""
    mock_connect = mocker.patch("miminet_model.psycopg2.connect")
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_connect.return_value.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    return mock_connect, mock_cursor


@pytest.fixture
def mock_sqlalchemy_inspect(mocker):
    """Mocks sqlalchemy.inspect."""
    mock_inspect = mocker.patch("miminet_model.inspect")
    mock_inspector = MagicMock()
    mock_inspect.return_value = mock_inspector
    return mock_inspector


@pytest.fixture
def mock_db(mocker):
    """Mocks the entire db object to prevent context errors with db.engine."""
    return mocker.patch("miminet_model.db")
