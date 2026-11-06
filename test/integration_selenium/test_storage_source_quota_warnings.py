from galaxy_test.driver.integration_util import ConfiguresObjectStores
from galaxy_test.selenium.framework import managed_history
from .framework import (
    selenium_test,
    SeleniumIntegrationTestCase,
)
from .test_objectstore_selection import MSI_EXAMPLE_OBJECT_STORE_CONFIG_TEMPLATE


class TestStorageSourceQuotaWarningsSeleniumIntegration(SeleniumIntegrationTestCase, ConfiguresObjectStores):
    ensure_registered = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        cls._configure_object_store(MSI_EXAMPLE_OBJECT_STORE_CONFIG_TEMPLATE, config)
        config["enable_quotas"] = True

    def _limit_second_tier_to_one_byte(self):
        response = self._post(
            "quotas",
            data={
                "name": self._get_random_name(prefix="secondtierquota"),
                "description": "tiny quota on the second tier",
                "amount": "1 bytes",
                "operation": "=",
                "default": "registered",
                "quota_source_label": "second_tier",
            },
            admin=True,
            json=True,
        )
        response.raise_for_status()

    @selenium_test
    @managed_history
    def test_warns_about_other_source_over_quota(self):
        self._limit_second_tier_to_one_byte()
        self.run_environment_test_tool(select_storage="second")
        self.history_panel_wait_for_hid_ok(1)

        # A fresh page load: nothing but the app's startup asks for the usage per source
        self.home()
        masthead = self.components.masthead
        masthead.other_storage_over_quota.wait_for_visible()
        warning = self.components.history_panel.other_sources_over_quota.wait_for_text()
        assert "Second Tier Storage" in warning

        # The popover has to stay open while the pointer moves onto its button
        self.hover(masthead.storage_dashboard_link.wait_for_visible())
        masthead.quota_source_over_quota.wait_for_visible()
        rows = [row.text for row in masthead.quota_source_usage.all()]
        assert any("Default storage" in row for row in rows), rows
        assert sum("on hold" in row for row in rows) == 1, rows
        assert any("Second Tier Storage" in row and "on hold" in row for row in rows), rows
        self.screenshot("quota_sources_popover_over_quota")

        masthead.storage_dashboard_button.wait_for_and_click()
        labels = self.components.storage_dashboard.source_label
        labels.wait_for_visible()
        assert "Second Tier Storage" in [label.text for label in labels.all()]

    @selenium_test
    def test_anonymous_user_is_offered_login(self):
        self.logout_if_needed()
        self.home()
        masthead = self.components.masthead
        self.hover(masthead.storage_dashboard_link.wait_for_visible())
        masthead.quota_sources_log_in_button.wait_for_and_click()
        self.components.login.form.wait_for_visible()
