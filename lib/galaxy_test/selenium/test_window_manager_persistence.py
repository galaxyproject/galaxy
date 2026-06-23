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
        self.execute_script("localStorage.removeItem('galaxy-window-manager-windows');")

    @selenium_test
    @managed_history
    def test_scratchbook_window_persistence(self):
        """Progressive test: open, reload, multi-window, close, verify persistence at each step."""
        self.perform_upload(self.get_filename("1.fasta"))
        self.perform_upload(self.get_filename("1.bed"))
        self.history_panel_wait_for_hid_ok(2)

        self.window_manager_enable()

        # Open dataset 1 in a window
        item1 = self.history_panel_item_component(hid=1)
        item1.display_button.wait_for_and_click()
        self.components.window_manager._.wait_for_visible()
        assert self.window_manager_window_count() == 1

        # Reload and verify 1 window restored with correct title
        self.sleep_for(self.wait_types.UX_RENDER)
        self.home()
        self.components.window_manager._.wait_for_visible()

        @retry_assertion_during_transitions
        def assert_one_window():
            assert self.window_manager_window_count() == 1

        assert_one_window()
        titles = self.window_manager_get_titles()
        assert len(titles) == 1
        assert "1:" in titles[0]
        self.screenshot("persistence_single_restored")

        # Open dataset 2 so we have 2 windows
        item2 = self.history_panel_item_component(hid=2)
        self.clear_tooltips()
        item2.display_button.wait_for_and_click()
        self.window_manager_wait_for_window_count(2)

        # Reload and verify both windows restored
        self.sleep_for(self.wait_types.UX_RENDER)
        self.home()
        self.window_manager_wait_for_window_count(2)
        titles = self.window_manager_get_titles()
        assert len(titles) == 2
        self.screenshot("persistence_multi_restored")

        # Close 1 of 2 windows, note the survivor
        self.window_manager_close_window(0)
        self.window_manager_wait_for_window_count(1)
        surviving_title = self.window_manager_get_titles()[0]
        self.sleep_for(self.wait_types.UX_RENDER)

        # Reload and verify only the survivor restored
        self.home()

        @retry_assertion_during_transitions
        def assert_survivor_restored():
            assert self.window_manager_window_count() == 1

        assert_survivor_restored()
        titles = self.window_manager_get_titles()
        assert len(titles) == 1
        assert titles[0] == surviving_title
        self.screenshot("persistence_partial_close_restored")

        # Close remaining window
        self.window_manager_close_window(0)
        self.window_manager_wait_for_window_count(0)
        self.sleep_for(self.wait_types.UX_RENDER)

        # Reload and verify no windows restored
        self.home()
        self.sleep_for(self.wait_types.UX_RENDER)
        assert self.window_manager_window_count() == 0
        self.screenshot("persistence_all_closed")
