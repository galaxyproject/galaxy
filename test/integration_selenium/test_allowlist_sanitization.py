from .framework import (
    selenium_test,
    SeleniumIntegrationTestCase,
)


class TestAllowListSanitization(SeleniumIntegrationTestCase):
    run_as_admin = True
    axe_skip = True  # skip testing iframe contents

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["sanitize_all_html"] = True

    def run_html_output(self):
        history_id = self.dataset_populator.new_history()
        run_response = self.dataset_populator.run_tool("html_output", {}, history_id=history_id)
        hda_id = run_response["outputs"][0]["id"]
        self.dataset_populator.wait_for_dataset(history_id, dataset_id=hda_id)
        return hda_id

    @selenium_test
    def test_html_output_sanitized(self):
        self.login()
        hda_id = self.run_html_output()
        self.get(f"datasets/{hda_id}/preview")
        self.wait_for_selector_visible("[data-description='sanitization warning']")
        self.assert_selector_absent("[data-description='allowlist link']")
        self.screenshot("sanitization warning")
        assert self.switch_to_frame()
        self.assert_selector_absent("[data-description='hello-world']")

    @selenium_test
    def test_html_output_sanitized_admin(self):
        self.admin_login()
        hda_id = self.run_html_output()
        self.get(f"datasets/{hda_id}/preview")
        self.wait_for_selector_visible("[data-description='sanitization warning']")
        self.wait_for_selector_visible("[data-description='allowlist link']")
        self.screenshot("sanitization warning admin")
        try:
            self._put(
                "/api/sanitize_allow?tool_id=html_output", data={"params": {"tool_id": "html_output"}}, admin=True
            ).raise_for_status()
            self.driver.refresh()
            self.assert_selector_absent("[data-description='sanitization warning']")
            self.assert_selector_absent("[data-description='allowlist link']")
            assert self.switch_to_frame()
            self.wait_for_selector("[data-description='hello-world']")
        finally:
            self._delete("/api/sanitize_allow?tool_id=html_output", admin=True)
