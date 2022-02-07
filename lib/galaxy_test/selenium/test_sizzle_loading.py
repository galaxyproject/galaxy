from .framework import (
    selenium_test,
    SeleniumTestCase,
)


class SizzleLoadingTestCase(SeleniumTestCase):
    @selenium_test
    def test_sizzle_loads(self):
        self.home()
        self.wait_for_sizzle_selector_clickable("div")
