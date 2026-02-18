"""E2E tests for Galaxy's Window Manager (WinBox floating windows)."""

from .framework import (
    managed_history,
    retry_assertion_during_transitions,
    selenium_test,
    SeleniumTestCase,
)


class TestWindowManager(SeleniumTestCase):
    ensure_registered = True

    @selenium_test
    def test_toggle_window_manager(self):
        """Toggle the window manager on and off via the masthead button."""
        self.home()

        # Initially inactive
        assert not self.window_manager_is_active()

        # Enable
        self.window_manager_toggle()
        assert self.window_manager_is_active()
        self.screenshot("window_manager_enabled")

        # Disable
        self.window_manager_toggle()
        assert not self.window_manager_is_active()
        self.screenshot("window_manager_disabled")

    @selenium_test
    @managed_history
    def test_open_dataset_in_window(self):
        """Display a dataset with WM active — a WinBox window should appear."""
        self.perform_upload(self.get_filename("1.fasta"))
        self.history_panel_wait_for_hid_ok(1)

        self.window_manager_enable()
        assert self.window_manager_window_count() == 0

        # Click the display button on HID 1
        item = self.history_panel_item_component(hid=1)
        item.display_button.wait_for_and_click()

        # A WinBox window should appear
        self.components.window_manager._.wait_for_visible()
        assert self.window_manager_window_count() == 1
        self.screenshot("window_manager_dataset_opened")

        # Verify the window title contains the HID
        titles = self.window_manager_get_titles()
        assert len(titles) == 1
        assert "1:" in titles[0]

    @selenium_test
    @managed_history
    def test_window_content_loads(self):
        """Content inside the WinBox iframe should render the dataset view."""
        self.perform_upload(self.get_filename("1.fasta"))
        self.history_panel_wait_for_hid_ok(1)

        self.window_manager_enable()
        item = self.history_panel_item_component(hid=1)
        item.display_button.wait_for_and_click()
        self.components.window_manager._.wait_for_visible()

        # Switch into the iframe and verify dataset view rendered
        with self.winbox_frame(0):
            self.wait_for_selector_visible(".dataset-view")
            self.screenshot("window_manager_iframe_content")

    @selenium_test
    @managed_history
    def test_multiple_windows(self):
        """Opening multiple datasets creates multiple WinBox windows with correct focus."""
        for _i in range(3):
            self.perform_upload(self.get_filename("1.fasta"))
        self.history_panel_wait_for_hid_ok(3)

        self.window_manager_enable()

        # Open datasets 1, 2, 3 in windows
        for hid in [1, 2, 3]:
            item = self.history_panel_item_component(hid=hid)
            self.clear_tooltips()
            item.display_button.wait_for_and_click()

        self.window_manager_wait_for_window_count(3)
        self.screenshot("window_manager_three_windows")

        # Verify titles
        titles = self.window_manager_get_titles()
        assert len(titles) == 3
        for hid in [1, 2, 3]:
            assert any(f"{hid}:" in t for t in titles), f"HID {hid} not found in titles: {titles}"

        # At least one window should exist with focus class
        focused_count = self.window_manager_focused_count()
        assert focused_count == 1, f"Expected exactly 1 focused window, got {focused_count}"

    @selenium_test
    @managed_history
    def test_close_window(self):
        """Closing a WinBox window removes it from DOM and decrements counter."""
        self.perform_upload(self.get_filename("1.fasta"))
        self.perform_upload(self.get_filename("1.bed"))
        self.history_panel_wait_for_hid_ok(2)

        self.window_manager_enable()

        # Open 2 windows
        for hid in [1, 2]:
            item = self.history_panel_item_component(hid=hid)
            self.clear_tooltips()
            item.display_button.wait_for_and_click()

        self.window_manager_wait_for_window_count(2)
        self.screenshot("window_manager_before_close")

        # Close one window
        self.window_manager_close_window(0)

        self.window_manager_wait_for_window_count(1)
        self.screenshot("window_manager_after_close")

        # Close the remaining window
        self.window_manager_close_window(0)
        self.window_manager_wait_for_window_count(0)

        # Verify no windows remain
        assert self.window_manager_window_count() == 0

    @selenium_test
    @managed_history
    def test_display_only_in_window(self):
        """Windowed dataset view should have displayOnly=true in iframe URL."""
        self.perform_upload(self.get_filename("1.fasta"))
        self.history_panel_wait_for_hid_ok(1)

        self.window_manager_enable()
        item = self.history_panel_item_component(hid=1)
        item.display_button.wait_for_and_click()
        self.components.window_manager._.wait_for_visible()

        # Verify the iframe URL contains the expected params
        iframe_src = self.window_manager_get_iframe_src(0)
        assert "displayOnly=true" in iframe_src, f"Expected displayOnly in URL: {iframe_src}"
        assert "hide_panels=true" in iframe_src, f"Expected hide_panels in URL: {iframe_src}"
        assert "hide_masthead=true" in iframe_src, f"Expected hide_masthead in URL: {iframe_src}"
        self.screenshot("window_manager_display_only")

    @selenium_test
    @managed_history
    def test_normal_navigation_when_disabled(self):
        """With WM disabled, display button navigates to dataset view normally."""
        self.perform_upload(self.get_filename("1.fasta"))
        self.history_panel_wait_for_hid_ok(1)

        # Ensure WM is OFF
        self.window_manager_disable()
        assert not self.window_manager_is_active()

        # Click display — should navigate normally
        item = self.history_panel_item_component(hid=1)
        item.display_button.wait_for_and_click()

        # Dataset view should render in main content area
        self.components.dataset_view._.wait_for_visible()
        assert self.window_manager_window_count() == 0
        self.screenshot("window_manager_off_normal_nav")

    @selenium_test
    @managed_history
    def test_focus_switching(self):
        """Clicking an unfocused window brings it to front (focus class)."""
        self.perform_upload(self.get_filename("1.fasta"))
        self.perform_upload(self.get_filename("1.bed"))
        self.history_panel_wait_for_hid_ok(2)

        self.window_manager_enable()

        # Open both datasets in windows
        for hid in [1, 2]:
            item = self.history_panel_item_component(hid=hid)
            self.clear_tooltips()
            item.display_button.wait_for_and_click()

        self.window_manager_wait_for_window_count(2)

        # Window 2 (last opened) should have focus
        focused_title = self.window_manager_get_focused_title()
        assert "2:" in focused_title, f"Expected window 2 focused, got: '{focused_title}'"
        self.screenshot("window_manager_focus_on_second")

        # Click the first window's focus overlay to switch focus
        self.window_manager_click_focus_overlay(0)

        # Now window 1 should have focus
        @retry_assertion_during_transitions
        def assert_focus_switched():
            new_focused = self.window_manager_get_focused_title()
            assert "1:" in new_focused, f"Expected window 1 focused, got: '{new_focused}'"

        assert_focus_switched()

        # Verify exactly one window has focus
        focused_count = self.window_manager_focused_count()
        assert focused_count == 1, f"Expected 1 focused window, got {focused_count}"
        self.screenshot("window_manager_focus_switched")
