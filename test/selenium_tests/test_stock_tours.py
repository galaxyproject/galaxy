import os

from .framework import SeleniumTestCase
from .framework import selenium_test

from galaxy.util import galaxy_root_path

STOCK_TOURS_DIRECTORY = os.path.join(galaxy_root_path, "config", "plugins", "tours")


class TestStockToursTestCase(SeleniumTestCase):

    @selenium_test
    def test_core_galaxy_ui(self):
        sleep_on_steps = {
            "Tools": 20,  # Give upload a chance to take so tool form is filled in.
            "History": 20,
        }
        self.run_tour(
            os.path.join(STOCK_TOURS_DIRECTORY, "core.galaxy_ui.yaml"),
            sleep_on_steps=sleep_on_steps,
        )

    @selenium_test
    def test_core_scratchbook(self):
        self.run_tour(
            os.path.join(STOCK_TOURS_DIRECTORY, "core.scratchbook.yaml"),
        )

    @selenium_test
    def test_core_history(self):
        self.run_tour(
            os.path.join(STOCK_TOURS_DIRECTORY, "core.history.yaml"),
        )
