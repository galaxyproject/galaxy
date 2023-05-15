from unittest import SkipTest

import pytest

from .framework import (
    selenium_test,
    SeleniumTestCase,
)


class TestTutorialMode(SeleniumTestCase):
    @selenium_test
    @pytest.mark.gtn_screenshot
    def test_activate_tutorial_mode(self):
        self._ensure_tutorial_mode_available()
        self.home()
        self.screenshot("tutorial_mode_0_0")
        self.tutorial_mode_activate()
        self.screenshot("tutorial_mode_0_1")

        # Access inside the frame
        self.driver.switch_to.frame("gtn-embed")
        self.wait_for_selector_visible("#top-navbar")
        self.screenshot("tutorial_mode_0_2")

    def _ensure_tutorial_mode_available(self):
        """Skip a test if the webhook GTN doesn't appear."""
        response = self.api_get("webhooks", raw=True)
        assert response.status_code == 200
        data = response.json()
        webhooks = [x["id"] for x in data]
        if "gtn" not in webhooks:
            raise SkipTest('Skipping test, webhook "GTN Tutorial Mode" doesn\'t appear to be configured.')
