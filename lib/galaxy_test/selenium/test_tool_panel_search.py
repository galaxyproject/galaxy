import json

from galaxy_test.base.populators import skip_without_tool

from .framework import (
    playwright_only,
    selenium_test,
    SeleniumTestCase,
)


class TestToolPanelSearchPlaywright(SeleniumTestCase):
    def _favorite_top_level_order(self):
        items = self.page.locator('[data-description="favorites-top-level-list"] > .favorite-top-level-item')
        order = []
        for index in range(items.count()):
            item = items.nth(index)
            order.append((item.get_attribute("data-favorite-type"), item.get_attribute("data-favorite-id")))
        return order

    def _favorite_order_from_api(self, user_id):
        user_response = self._get(f"users/{user_id}")
        assert user_response.status_code == 200, user_response.text
        favorites = user_response.json()["preferences"]["favorites"]
        if isinstance(favorites, str):
            favorites = json.loads(favorites)
        return favorites["order"]

    def _drag_favorite_item_above(self, source_type, target_type):
        source_handle = self.page.locator(
            f'[data-favorite-type="{source_type}"] [data-description="favorite-top-level-drag-target"]'
        )
        target_item = self.page.locator(f'[data-favorite-type="{target_type}"]')
        source_handle.scroll_into_view_if_needed()
        target_item.scroll_into_view_if_needed()
        source_box = source_handle.bounding_box()
        target_box = target_item.bounding_box()
        assert source_box is not None
        assert target_box is not None

        source_x = source_box["x"] + (source_box["width"] / 2)
        source_y = source_box["y"] + (source_box["height"] / 2)
        target_x = target_box["x"] + (target_box["width"] / 2)
        target_y = target_box["y"] + min(8, target_box["height"] / 4)

        self.page.mouse.move(source_x, source_y)
        self.page.mouse.down()
        self.page.mouse.move(source_x, source_y + 12, steps=4)
        self.page.mouse.move(target_x, target_y, steps=20)
        self.page.mouse.up()

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

    @playwright_only("Validates mixed-type top-level favorite reordering with Playwright backend.")
    @selenium_test
    @skip_without_tool("cat1")
    def test_tool_panel_favorites_reorder_my_panel(self):
        self.login()
        user_id = self.api_get("users/current")["id"]

        tool_favorite_response = self._put(
            f"users/{user_id}/favorites/tools",
            data={"object_id": "cat1"},
            json=True,
        )
        assert tool_favorite_response.status_code == 200, tool_favorite_response.text

        tag_favorite_response = self._put(
            f"users/{user_id}/favorites/tags",
            data={"object_id": "Text Manipulation"},
            json=True,
        )
        assert tag_favorite_response.status_code == 200, tag_favorite_response.text

        self.home()
        self.open_toolbox()
        self.swap_to_tool_panel("my_panel")

        tool_panel = self.components.tool_panel
        tool_panel.toolbox.wait_for_visible()
        self.wait_for_selector('[data-description="favorites-top-level-list"]')
        self.wait_for_selector('[data-favorite-type="tools"][data-favorite-id="cat1"]')
        self.wait_for_selector('[data-favorite-type="tags"][data-favorite-id="Text Manipulation"]')

        assert self._favorite_top_level_order()[:2] == [
            ("tools", "cat1"),
            ("tags", "Text Manipulation"),
        ]

        self._drag_favorite_item_above("tags", "tools")

        expected_order = [
            {"object_type": "tags", "object_id": "Text Manipulation"},
            {"object_type": "tools", "object_id": "cat1"},
        ]
        self._wait_on(
            lambda: self._favorite_order_from_api(user_id)[:2] == expected_order,
            "favorite order to persist after drag-and-drop",
        )
        self._wait_on(
            lambda: self._favorite_top_level_order()[:2]
            == [
                ("tags", "Text Manipulation"),
                ("tools", "cat1"),
            ],
            "favorite tool panel order to update after drag-and-drop",
        )
