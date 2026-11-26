from typing import TYPE_CHECKING

from galaxy_test.driver import integration_util
from galaxy_test.selenium import framework

if TYPE_CHECKING:
    from galaxy_test.selenium.framework import SeleniumSessionDatasetPopulator

selenium_test = framework.selenium_test
managed_history = framework.managed_history


class SeleniumIntegrationTestCase(
    integration_util.IntegrationTestCase, framework.TestWithSeleniumMixin, framework.UsesLibraryAssertions
):
    dataset_populator: "SeleniumSessionDatasetPopulator"

    def setup_method(self):
        # pytest skips teardown_method when setup_method raises, so tear the
        # driver down here when a subclass setUp fails after allocating it.
        with self._tear_down_driver_on_error():
            super().setup_method()

    def setUp(self):
        super().setUp()
        self.setup_selenium()

    def tearDown(self):
        self.tear_down_selenium()
        super().tearDown()

    def restart(self, handle_reconfig=None):
        super().restart(handle_reconfig=handle_reconfig)
        self.reset_driver_and_session()


__all__ = (
    "selenium_test",
    "SeleniumIntegrationTestCase",
)
