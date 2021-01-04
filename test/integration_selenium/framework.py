from galaxy_test.driver import integration_util
from galaxy_test.selenium import (
    framework
)

selenium_test = framework.selenium_test


class SeleniumIntegrationTestCase(integration_util.IntegrationTestCase, framework.TestWithSeleniumMixin):

    def setUp(self):
        super().setUp()
        self.setup_selenium()

    def tearDown(self):
        self.tear_down_selenium()
        super().tearDown()


__all__ = (
    'selenium_test',
    'SeleniumIntegrationTestCase',
)
