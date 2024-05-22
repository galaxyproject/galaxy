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
