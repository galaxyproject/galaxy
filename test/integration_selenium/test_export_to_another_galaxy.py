from .framework import (
    managed_history,
    selenium_test,
    SeleniumIntegrationTestCase,
)


class TestExportToAnotherGalaxySeleniumIntegration(SeleniumIntegrationTestCase):
    ensure_registered = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["short_term_storage_default_duration"] = 172800

    @selenium_test
    @managed_history
    def test_dialog_states_the_link_lifetime_of_this_server(self):
        self.dataset_populator.new_dataset(self.current_history_id(), content="1\n", wait=True)
        self.home()
        self.history_panel_wait_for_hid_ok(1)
        item = self.history_panel_ensure_showing_item_details(1)
        item.export_to_another_galaxy_button.wait_for_and_click()
        dialog = self.components.export_to_another_galaxy
        dialog.link.wait_for_visible()
        assert "usually after 2 days" in dialog.link_warning.wait_for_text()
