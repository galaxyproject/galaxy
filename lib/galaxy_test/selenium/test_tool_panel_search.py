from .framework import (
    playwright_only,
    selenium_test,
    SeleniumTestCase,
)


class TestToolPanelSearchPlaywright(SeleniumTestCase):
    @playwright_only("Validates tool panel search behavior with Playwright backend.")
    @selenium_test
    def test_tool_panel_search_my_panel(self):
        self.home()
        self.open_toolbox()
        self.swap_to_tool_panel("my_panel")

        tool_panel = self.components.tool_panel
        tool_panel.toolbox.wait_for_visible()

        search = self.components.tools.search
        search.wait_for_visible()
        search.wait_for_and_send_keys("filter failed")

        tool_panel.tool_link(tool_id="__FILTER_FAILED_DATASETS__").wait_for_visible()

    @playwright_only("Validates tool panel favorites/recents behavior with Playwright backend.")
    @selenium_test
    def test_tool_panel_favorites_and_recents_my_panel(self):
        self.login()

        self.home()
        self.open_toolbox()
        self.swap_to_tool_panel("my_panel")

        tool_panel = self.components.tool_panel
        tool_panel.toolbox.wait_for_visible()

        favorites_label_selector = ".tool-panel-label:has-text('Favorites')"
        recents_label_selector = ".tool-panel-label:has-text('Recent tools')"
        empty_alert_selector = ".tool-panel-empty .alert"

        self.wait_for_selector(favorites_label_selector)
        empty_alert = self.wait_for_selector(empty_alert_selector)
        assert "haven't favorited any tools yet" in empty_alert.text
        self.wait_for_selector_absent_or_hidden(recents_label_selector)

        search = self.components.tools.search
        search.wait_for_visible()
        search.wait_for_and_send_keys("create_2")
        tool_panel.tool_link(tool_id="create_2").wait_for_and_click()

        self.components.tool_form.execute.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)

        self.home()
        self.open_toolbox()
        self.swap_to_tool_panel("my_panel")
        tool_panel.toolbox.wait_for_visible()

        self.wait_for_selector(recents_label_selector)
        tool_panel.tool_link(tool_id="create_2").wait_for_visible()
        empty_alert = self.wait_for_selector(empty_alert_selector)
        assert "haven't favorited any tools yet" in empty_alert.text

        self.wait_for_selector('[data-description="clear-recent-tools"]').click()
        self.wait_for_selector_absent_or_hidden(recents_label_selector)

        search = self.components.tools.search
        search.wait_for_visible()
        search.wait_for_and_send_keys("filter failed")
        tool_panel.tool_link(tool_id="__FILTER_FAILED_DATASETS__").wait_for_visible()

        favorite_button_selector = '.tool-favorite-button[data-tool-id="__FILTER_FAILED_DATASETS__"]'
        favorite_button = self.wait_for_selector(favorite_button_selector)
        favorite_button.click()

        self.components.tools.clear_search.wait_for_and_click()

        tool_panel.tool_link(tool_id="__FILTER_FAILED_DATASETS__").wait_for_visible()
        self.wait_for_selector_absent_or_hidden(empty_alert_selector)

        self.page.locator(favorite_button_selector).focus()
        self.page.keyboard.press("Enter")

        self.wait_for_selector_absent_or_hidden('.toolTitle a[data-tool-id="__FILTER_FAILED_DATASETS__"]')
        empty_alert = self.wait_for_selector(empty_alert_selector)
        assert "haven't favorited any tools yet" in empty_alert.text

        search.wait_for_visible()
        search.wait_for_and_send_keys("filter failed")
        favorite_button = self.wait_for_selector(favorite_button_selector)
        favorite_button.click()
        self.components.tools.clear_search.wait_for_and_click()

        tool_panel.tool_link(tool_id="__FILTER_FAILED_DATASETS__").wait_for_visible()
        self.wait_for_selector_absent_or_hidden(empty_alert_selector)

        search.wait_for_visible()
        search.wait_for_and_send_keys("filter")

        self.wait_for_selector(favorites_label_selector)
        self.wait_for_selector(".tool-panel-label:has-text('Search results')")

        tool_panel.tool_link(tool_id="__FILTER_FAILED_DATASETS__").wait_for_visible()
        tool_panel.tool_link(tool_id="filter_multiple_splitter").wait_for_visible()

        self.wait_for_selector(favorites_label_selector).click()
        self.wait_for_selector(".tool-panel-label[aria-expanded='false']:has-text('Favorites')")
        self.wait_for_selector_absent_or_hidden('.toolTitle a[data-tool-id="__FILTER_FAILED_DATASETS__"]')
        tool_panel.tool_link(tool_id="filter_multiple_splitter").wait_for_visible()
