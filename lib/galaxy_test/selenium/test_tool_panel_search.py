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

    def _favorite_order_from_api(self, interactor, user_id):
        user_response = interactor.get(f"users/{user_id}")
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
        self.playwright_drag_item_above(source_handle, target_item)

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

    @playwright_only("Validates mixed-type top-level favorite reordering with Playwright backend.")
    @selenium_test
    @skip_without_tool("cat1")
    def test_tool_panel_favorites_reorder_my_panel(self):
        self.login()
        interactor = self.api_interactor_for_logged_in_user()
        user_response = interactor.get("users/current")
        assert user_response.status_code == 200, user_response.text
        user_id = user_response.json()["id"]

        tool_favorite_response = interactor.put(
            f"users/{user_id}/favorites/tools",
            data={"object_id": "cat1"},
            json=True,
        )
        assert tool_favorite_response.status_code == 200, tool_favorite_response.text

        tag_favorite_response = interactor.put(
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
            lambda: self._favorite_order_from_api(interactor, user_id)[:2] == expected_order,
            "favorite order to persist after drag-and-drop",
        )
        self._wait_on(
            lambda: (
                self._favorite_top_level_order()[:2]
                == [
                    ("tags", "Text Manipulation"),
                    ("tools", "cat1"),
                ]
            ),
            "favorite tool panel order to update after drag-and-drop",
        )
