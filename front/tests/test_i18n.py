import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from conftest import MiminetTester, MAIN_PAGE
from utils.networks import MiminetTestNetwork
from utils.locators import Location


class TestI18n:
    """Тесты для проверки работы локализации (i18n)"""

    @pytest.fixture(scope="class")
    def empty_network(self, selenium: MiminetTester):
        """Создаём пустую сеть для тестов"""
        empty_network = MiminetTestNetwork(selenium)
        yield empty_network.url
        empty_network.delete()

    def _switch_language(self, selenium: MiminetTester, lang: str):
        """Переключает язык интерфейса"""
        # Ждём появления и кликабельности кнопки переключения языка
        language_dropdown = WebDriverWait(selenium, 10).until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, Location.NavigationButton.LANGUAGE_DROPDOWN.selector)
            )
        )
        # Прокручиваем элемент в видимую область
        selenium.execute_script("arguments[0].scrollIntoView({behavior: 'auto', block: 'center'});", language_dropdown)
        language_dropdown.click()

        # Ждём, пока откроется меню выбора языка
        WebDriverWait(selenium, 10).until(
            EC.presence_of_element_located(
                (By.XPATH, f"//a[contains(@onclick, \"setLanguage('{lang}')\")]")
            )
        )

        # Ждём кликабельности элемента языка
        lang_link = WebDriverWait(selenium, 10).until(
            EC.element_to_be_clickable(
                (By.XPATH, f"//a[contains(@onclick, \"setLanguage('{lang}')\")]")
            )
        )
        lang_link.click()

        # Ждём применения перевода через проверку lang у <html>
        WebDriverWait(selenium, 10).until(
            lambda driver: driver.execute_script("return document.documentElement.lang")
            == lang
        )
        
        # Небольшая задержка для стабилизации интерфейса
        import time
        time.sleep(0.5)

    def test_language_switcher_exists(self, selenium: MiminetTester):
        """Проверяет, что кнопка переключения языка существует на главной странице"""
        selenium.get(MAIN_PAGE)
        
        language_button = WebDriverWait(selenium, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, Location.NavigationButton.LANGUAGE_DROPDOWN.selector)
            )
        )
        assert language_button.is_displayed()

    def test_main_page_translation(self, selenium: MiminetTester):
        """Проверяет перевод текстов на главной странице"""
        selenium.get(MAIN_PAGE)

        # Явно задаем русский язык перед стартом проверок
        self._switch_language(selenium, "ru")
        
        create_button = WebDriverWait(selenium, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, Location.MainPage.CREATE_NETWORK_BUTTON.selector)
            )
        )
        assert "Создать сеть" in create_button.text

        # Переключаемся на английский
        self._switch_language(selenium, "en")
        
        create_button = WebDriverWait(selenium, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, Location.MainPage.CREATE_NETWORK_BUTTON.selector)
            )
        )
        assert "Create a network" in create_button.text

    def test_network_page_translation(
        self, selenium: MiminetTester, empty_network: str
    ):
        """Проверяет перевод текстов на странице сети"""
        selenium.get(empty_network)

        self._switch_language(selenium, "ru")

        # Проверяем русский язык
        emulate_button = WebDriverWait(selenium, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, Location.Network.EMULATE_BUTTON.selector)
            )
        )
        assert "Эмулировать" in emulate_button.text

        # Проверяем кнопки в шапке
        share_button = WebDriverWait(selenium, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, Location.Network.TopButton.SHARE.selector)
            )
        )
        copy_button = WebDriverWait(selenium, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, Location.Network.TopButton.COPY.selector)
            )
        )
        settings_button = WebDriverWait(selenium, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, Location.Network.TopButton.OPTIONS.selector)
            )
        )

        # Переключаемся на английский
        self._switch_language(selenium, "en")

        # Проверяем, что кнопка эмуляции переведена
        emulate_button = WebDriverWait(selenium, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, Location.Network.EMULATE_BUTTON.selector)
            )
        )
        assert "Emulate" in emulate_button.text

        # Проверяем, что кнопки в шапке остались (они должны быть видимы)
        assert share_button.is_displayed()
        assert copy_button.is_displayed()
        assert settings_button.is_displayed()

    def test_network_player_label_translation(
        self, selenium: MiminetTester, empty_network: str
    ):
        """Проверяет перевод меток плеера сети"""
        selenium.get(empty_network)

        self._switch_language(selenium, "ru")

        # Проверяем начальную метку ожидания на русском
        wait_label = WebDriverWait(selenium, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, Location.Network.PLAYER_LABEL.selector)
            )
        )
        assert "Ожидание" in wait_label.text

        # Переключаемся на английский
        self._switch_language(selenium, "en")

        # Проверяем, что метка переведена
        wait_label = WebDriverWait(selenium, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, Location.Network.PLAYER_LABEL.selector)
            )
        )
        assert "Waiting" in wait_label.text

    def test_ask_question_button_with_icon(
        self, selenium: MiminetTester, empty_network: str
    ):
        """Проверяет, что кнопка 'Задать вопрос' содержит иконку Telegram на обоих языках"""
        selenium.get(empty_network)
        self._switch_language(selenium, "ru")

        # Проверяем на русском
        ask_button = WebDriverWait(selenium, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, Location.Network.ASK_QUESTION_BUTTON.selector)
            )
        )

        # Проверяем, что есть иконка
        icon = ask_button.find_element(By.TAG_NAME, "img")
        assert icon.get_attribute("src") is not None
        assert "tg_logo.png" in icon.get_attribute("src")
        assert "Задать вопрос" in ask_button.text

        # Переключаемся на английский
        self._switch_language(selenium, "en")

        # Проверяем, что иконка осталась
        ask_button = WebDriverWait(selenium, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, Location.Network.ASK_QUESTION_BUTTON.selector)
            )
        )
        icon = ask_button.find_element(By.TAG_NAME, "img")
        assert icon.get_attribute("src") is not None
        assert "tg_logo.png" in icon.get_attribute("src")
        assert "Ask a question" in ask_button.text

    def test_language_persistence(self, selenium: MiminetTester):
        """Проверяет, что выбранный язык сохраняется после перезагрузки страницы"""
        selenium.get(MAIN_PAGE)

        # Переключаемся на английский
        self._switch_language(selenium, "en")

        # Проверяем, что язык установлен
        lang = selenium.execute_script("return document.documentElement.lang")
        assert lang == "en"

        # Перезагружаем страницу
        selenium.refresh()

        # Ждём загрузки и проверяем язык
        WebDriverWait(selenium, 10).until(
            lambda driver: driver.execute_script("return document.documentElement.lang")
            == "en"
        )

        # Проверяем, что текст переведён
        create_button = WebDriverWait(selenium, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, Location.MainPage.CREATE_NETWORK_BUTTON.selector)
            )
        )
        assert "Create a network" in create_button.text

    def test_multiple_language_switches(
        self, selenium: MiminetTester, empty_network: str
    ):
        """Проверяет множественные переключения языка туда-сюда"""
        selenium.get(empty_network)

        for _ in range(3):
            # Переключаемся на английский
            self._switch_language(selenium, "en")
            emulate_button = WebDriverWait(selenium, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, Location.Network.EMULATE_BUTTON.selector)
                )
            )
            assert "Emulate" in emulate_button.text

            # Переключаемся на русский
            self._switch_language(selenium, "ru")
            emulate_button = WebDriverWait(selenium, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, Location.Network.EMULATE_BUTTON.selector)
                )
            )
            assert "Эмулировать" in emulate_button.text

    def test_navigation_buttons_translation(self, selenium: MiminetTester):
        """Проверяет перевод кнопок навигации"""
        selenium.get(MAIN_PAGE)

        self._switch_language(selenium, "ru")

        # Проверяем русский
        my_networks = WebDriverWait(selenium, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, Location.NavigationButton.MY_NETWORKS_BUTTON.selector)
            )
        )
        assert "Мои сети" in my_networks.text

        # Переключаемся на английский
        self._switch_language(selenium, "en")
        my_networks = WebDriverWait(selenium, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, Location.NavigationButton.MY_NETWORKS_BUTTON.selector)
            )
        )
        assert "My Networks" in my_networks.text