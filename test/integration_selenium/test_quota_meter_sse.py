"""E2E test that the masthead quota meter follows ``user_quota_update`` events."""

from uuid import uuid4

from galaxy.util.wait import wait_on
from galaxy_test.selenium.framework import selenium_test
from .framework import SeleniumIntegrationTestCase

SSE_CONNECT_TIMEOUT_SECONDS = 15
QUOTA_METER_TIMEOUT_SECONDS = 15


class TestQuotaMeterSSESeleniumIntegration(SeleniumIntegrationTestCase):
    ensure_registered = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["enable_celery_tasks"] = False
        config["enable_sse_updates"] = True
        config["enable_quotas"] = True

    @selenium_test
    def test_quota_meter_updates_when_admin_assigns_quota(self):
        self.home()
        wait_on(
            lambda: True if self.execute_script("return window.__galaxy_sse_connected === true") else None,
            "window.__galaxy_sse_connected === true",
            timeout=SSE_CONNECT_TIMEOUT_SECONDS,
        )
        meter = self.components.masthead.storage_dashboard_link
        # Without a quota the meter shows the usage only
        assert " of " not in meter.wait_for_visible().text

        user_id = self.api_get("users/current")["id"]
        self.dataset_populator.create_quota(
            {
                "name": f"quota_{uuid4()}",
                "description": "Quota meter SSE test quota",
                "amount": "1TB",
                "operation": "=",
                "default": "no",
                "in_users": [user_id],
                "in_groups": [],
            }
        )

        # SSE connected, so the client doesn't refresh on its own: only the event can update the meter
        wait_on(
            lambda: True if " of " in meter.wait_for_visible().text else None,
            "quota meter showing the assigned quota",
            timeout=QUOTA_METER_TIMEOUT_SECONDS,
        )
