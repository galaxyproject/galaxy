from galaxy.selenium.has_driver import exception_indicates_not_clickable
from galaxy.selenium.navigates_galaxy import exception_seems_to_indicate_transition
from .framework import (
    selenium_test,
    SeleniumTestCase,
)


class TestNavigatesGalaxySelenium(SeleniumTestCase):
    """Test the Selenium test framework itself.

    Unlike the others test cases in this module, this test case tests the
    test framework itself (for when that makes sense, mostly corner cases).
    """

    @selenium_test
    def test_click_error(self):
        """Verify exception handling stuff by attempting to click on a disabled element in the UI."""
        self.home()
        self.upload_start_click()
        # Open the details, verify they are open and do a refresh.
        exception = None
        disabled_element_selector = ".show-history-content-selectors-btn"
        try:
            self.wait_for_selector(disabled_element_selector).click()
        except Exception as e:
            exception = e
        assert exception is not None
        assert exception_indicates_not_clickable(exception)
        assert exception_seems_to_indicate_transition(exception)
