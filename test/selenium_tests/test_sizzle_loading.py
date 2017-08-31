from .framework import SeleniumTestCase
from .framework import selenium_test


class SizzleLoadingTestCase(SeleniumTestCase):

    @selenium_test
    def test_sizzle_loads(self):
        self.home()
        self.wait_for_sizzle_selector_clickable("div")
