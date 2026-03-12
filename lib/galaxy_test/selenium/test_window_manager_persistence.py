"""E2E tests for scratchbook window persistence across page reloads."""

from .framework import (
    managed_history,
    retry_assertion_during_transitions,
    selenium_test,
    SeleniumTestCase,
)


class TestWindowManagerPersistence(SeleniumTestCase):
    ensure_registered = True

    def setUp(self):
        super().setUp()
        # Clear persisted scratchbook state so tests don't leak into each other.
        # Must happen before managed_history's home() call triggers restore().
        self.execute_script("localStorage.removeItem('galaxy-scratchbook-windows');")

    @selenium_test
    @managed_history
    def test_windows_persist_across_reload(self):
        """Open a dataset in a scratchbook window, reload, and verify it's restored."""
        self.perform_upload(self.get_filename("1.fasta"))
        self.history_panel_wait_for_hid_ok(1)

        self.window_manager_enable()
        item = self.history_panel_item_component(hid=1)
        item.display_button.wait_for_and_click()
        self.components.window_manager._.wait_for_visible()
        assert self.window_manager_window_count() == 1
        self.screenshot("persistence_before_reload")

        self.home()

        self.components.window_manager._.wait_for_visible()

        @retry_assertion_during_transitions
        def assert_window_restored():
            assert self.window_manager_window_count() == 1

        assert_window_restored()

        titles = self.window_manager_get_titles()
        assert len(titles) == 1
        assert "1:" in titles[0]
        self.screenshot("persistence_after_reload")

    @selenium_test
    @managed_history
    def test_multiple_windows_persist(self):
        """Multiple scratchbook windows should all restore after reload."""
        self.perform_upload(self.get_filename("1.fasta"))
        self.perform_upload(self.get_filename("1.bed"))
        self.history_panel_wait_for_hid_ok(2)

        self.window_manager_enable()
        for hid in [1, 2]:
            item = self.history_panel_item_component(hid=hid)
            self.clear_tooltips()
            item.display_button.wait_for_and_click()

        self.window_manager_wait_for_window_count(2)
        self.screenshot("persistence_multi_before_reload")

        self.home()

        self.window_manager_wait_for_window_count(2)

        titles = self.window_manager_get_titles()
        assert len(titles) == 2
        self.screenshot("persistence_multi_after_reload")

    @selenium_test
    @managed_history
    def test_closed_windows_not_restored(self):
        """Windows that were closed before reload should not come back."""
        self.perform_upload(self.get_filename("1.fasta"))
        self.history_panel_wait_for_hid_ok(1)

        self.window_manager_enable()
        item = self.history_panel_item_component(hid=1)
        item.display_button.wait_for_and_click()
        self.components.window_manager._.wait_for_visible()
        assert self.window_manager_window_count() == 1

        self.window_manager_close_window(0)
        self.window_manager_wait_for_window_count(0)

        self.home()
        self.sleep_for(self.wait_types.UX_RENDER)

        assert self.window_manager_window_count() == 0
        self.screenshot("persistence_closed_not_restored")

    @selenium_test
    @managed_history
    def test_close_one_of_many_persists_rest(self):
        """Close one of two windows, reload, verify only the survivor restores."""
        self.perform_upload(self.get_filename("1.fasta"))
        self.perform_upload(self.get_filename("1.bed"))
        self.history_panel_wait_for_hid_ok(2)

        self.window_manager_enable()
        for hid in [1, 2]:
            item = self.history_panel_item_component(hid=hid)
            self.clear_tooltips()
            item.display_button.wait_for_and_click()

        self.window_manager_wait_for_window_count(2)

        self.window_manager_close_window(0)
        self.window_manager_wait_for_window_count(1)

        surviving_title = self.window_manager_get_titles()[0]
        # Wait for the debounced save (200ms) to flush to localStorage
        self.sleep_for(self.wait_types.UX_RENDER)
        self.screenshot("persistence_partial_close_before_reload")

        self.home()

        @retry_assertion_during_transitions
        def assert_one_restored():
            assert self.window_manager_window_count() == 1

        assert_one_restored()

        titles = self.window_manager_get_titles()
        assert len(titles) == 1
        assert titles[0] == surviving_title
        self.screenshot("persistence_partial_close_after_reload")
