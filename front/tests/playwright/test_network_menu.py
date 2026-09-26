import pytest
from playwright.sync_api import Page, expect

from conftest import HOME_PAGE, MAIN_PAGE
from utils.locators import Location
from utils.networks import MiminetTestNetwork


class TestNetworkMenu:
    @pytest.fixture(scope="class")
    def empty_network(self, authorized_page: Page):
        empty_network = MiminetTestNetwork(authorized_page)

        yield empty_network.url

        empty_network.delete()

    def test_my_networks_button_press(self, authorized_page: Page):
        """Checks if it is possible to get to the network selection menu"""
        authorized_page.goto(MAIN_PAGE)
        authorized_page.click(Location.NavigationButton.MY_NETWORKS_BUTTON.selector)

        expect(authorized_page).to_have_url(HOME_PAGE)

    def test_new_network_existence(self, authorized_page: Page, empty_network: str):
        """Checks if the created network exists"""
        authorized_page.goto(empty_network)  # open new network by URL

        expect(
            authorized_page.locator(Location.Network.TITLE_LABEL.selector)
        ).to_have_text("Новая сеть")

    def test_new_network_open(self, authorized_page: Page, empty_network: str):
        """Checks is it possible to open new network via home menu

        The card is addressed by the link it carries rather than by its position
        among the siblings: the home page puts service cards ("create network",
        "task from AI") first, so a positional locator points at a different
        card whenever that leading group changes.
        """
        authorized_page.goto(HOME_PAGE)
        guid = empty_network.split("guid=")[1]
        authorized_page.click(f'a[href*="{guid}"]')

        expect(authorized_page).to_have_url(empty_network)
