import os

from galaxy.util import galaxy_root_path
from .framework import (
    selenium_test,
    SeleniumTestCase,
    TIMEOUT_MULTIPLIER,
)

STOCK_TOURS_DIRECTORY = os.path.join(galaxy_root_path, "config", "plugins", "tours")


class TestStockToursTestCase(SeleniumTestCase):
    @selenium_test
    def test_core_galaxy_ui(self):
        sleep_on_steps = {
            "Tools": 20 * TIMEOUT_MULTIPLIER,
            "Select a tool": 2 * TIMEOUT_MULTIPLIER,
            "History": 20 * TIMEOUT_MULTIPLIER,
        }
        self.run_tour(
            os.path.join(STOCK_TOURS_DIRECTORY, "core.galaxy_ui.yaml"),
            sleep_on_steps=sleep_on_steps,
            tour_callback=TourCallback(self),
        )

    @selenium_test
    def test_core_windows(self):
        self.run_tour(
            os.path.join(STOCK_TOURS_DIRECTORY, "core.windows.yaml"),
            tour_callback=TourCallback(self),
        )

    @selenium_test
    def test_core_history(self):
        self.run_tour(
            os.path.join(STOCK_TOURS_DIRECTORY, "core.history.yaml"),
            tour_callback=TourCallback(self),
        )

    @selenium_test
    def test_core_deferred(self):
        self.run_tour(
            os.path.join(STOCK_TOURS_DIRECTORY, "core.deferred.yaml"),
            tour_callback=TourCallback(self),
        )


class TourCallback:
    def __init__(self, test_case: TestStockToursTestCase):
        self.test_case = test_case

    def handle_step(self, step, step_index: int):
        self.test_case.assert_baseline_accessibility()
