from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium import webdriver


# Set path Selenium
CHROMEDRIVER_PATH = "/usr/local/bin/chromedriver"
s = Service(CHROMEDRIVER_PATH)
WINDOW_SIZE = "1920,1080"

# ImmutableMultiDict([('remember_token',
# '228|c35335c08c0b47101da22247ad8fa334a82c601de8ac463dad45972cb5f01a190bd8a23fe53bef275180cee71eb9ca0ffa6511cfc1d5df08e70cf5739b41e6e8')])


# def insert_fake_user():
#     from src.miminet_model import User, db
#     from werkzeug.security import generate_password_hash

#     old_user = User.query.filter(User.id == 228).first()
#     if old_user:
#         old_user.password = generate_password_hash("password")
#     else:
#         new_user = User(
#             id=228,
#             nick="selenium",
#             role=0,
#             email="selenium-email",
#             password_hash=generate_password_hash("password"),
#             avatar_uri="rofl.jpg",
#         )

#         db.session.add(new_user)
#     db.session.commit()


def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--window-size=%s" % WINDOW_SIZE)
    chrome_options.add_argument("--no-sandbox")

    print("here")
    return webdriver.Remote("http://localhost:4444/wd/hub", options=chrome_options)


# # Options

# session = requests.Session()
# response = session.post(
#     "http://localhost//auth/login.html",
#     data={"email": "selenium-email", "password": "password"},
# )

# cookies = session.cookies

# driver = get_driver()
# driver.get("http:\\localhost")

# for cookie in cookies:
#     if cookie.name and cookie.value and cookie.expires:
#         data = {
#             "domain": "localhost",
#             "expiry": cookie.expires,
#             "httpOnly": False,
#             "name": cookie.name,
#             "path": "/",
#             "sameSite": "Lax",
#             "secure": False,
#             "value": cookie.value,
#         }
#         driver.add_cookie(data)

# driver.get("http:\\localhost")
# driver.find_element(By.CLASS_NAME, "nav-link").click()
# print(driver.title)
# driver.current_url
# driver.close()

driver = get_driver()

print("here")
driver.get("http://172.19.0.2:80/")
driver.save_screenshot("123.png")

driver.close()
driver.quit()
