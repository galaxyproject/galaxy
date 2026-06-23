from galaxy.util.unittest_utils import transient_failure
from .framework import (
    playwright_only,
    selenium_test,
    SeleniumTestCase,
)


class TestToolDiscoveryViewAnonymous(SeleniumTestCase):
    """Test the Tool Discovery View (rich tools list).

    This view provides advanced tool search and discovery features,
    moving the advanced search from the tool panel sidebar to a
    dedicated center panel view (PR #20747).

    TODO: We should add tests for ontology filtering, section filtering,
    advanced search, and list vs grid view toggling.
    """

    FILTER_FAILED_TOOL_ID = "__FILTER_FAILED_DATASETS__"

    def _open_tools_list_with_filter_failed(self):
        """Navigate to the Tool Discovery view and search for the FILTER_FAILED tool.

        Most discovery-view tests want the tools list visible and the FILTER_FAILED
        card rendered before the test exercises a specific behavior on it.
        """
        self.home()
        self.components.tool_panel.discover_tools_link.wait_for_and_click()
        tools_list = self.components.tools_list
        tools_list._.wait_for_visible()
        tools_list.search_input.wait_for_and_send_keys("filter failed")
        tools_list.tool_card(tool_id=self.FILTER_FAILED_TOOL_ID).wait_for_visible()
        return tools_list

    @transient_failure(issue=21225, potentially_fixed=True)
    @selenium_test
    def test_tool_discovery_landing(self):
        """Discover-Tools link navigates to the rich tools list."""
        self.home()
        self.components.tool_panel.discover_tools_link.wait_for_and_click()
        tools_list = self.components.tools_list
        tools_list._.wait_for_visible()
        self.screenshot("tools_list_landing")

    @selenium_test
    def test_tool_discovery_search_renders_matching_card(self):
        tools_list = self._open_tools_list_with_filter_failed()
        self.screenshot("tools_list_filtered")
        tools_list.tool_card(tool_id=self.FILTER_FAILED_TOOL_ID).wait_for_visible()

    @selenium_test
    def test_tool_discovery_version_button(self):
        tools_list = self._open_tools_list_with_filter_failed()
        tools_list.version_button(tool_id=self.FILTER_FAILED_TOOL_ID).wait_for_and_click()
        self.screenshot("tools_list_show_version")

    @selenium_test
    def test_tool_discovery_favorite_button_prompts_login_anonymous(self):
        tools_list = self._open_tools_list_with_filter_failed()
        button = tools_list.favorite_tool_button(tool_id=self.FILTER_FAILED_TOOL_ID).wait_for_visible()
        assert button.get_attribute("title") == "Login or Register to Favorite Tools"

    @selenium_test
    def test_tool_discovery_help_toggle_shows_and_hides(self):
        tools_list = self._open_tools_list_with_filter_failed()
        tools_list.tool_help(tool_id=self.FILTER_FAILED_TOOL_ID).assert_absent()

        tools_list.toggle_help(tool_id=self.FILTER_FAILED_TOOL_ID).wait_for_and_click()
        tools_list.tool_help(tool_id=self.FILTER_FAILED_TOOL_ID).wait_for_visible()
        self.screenshot("tools_list_show_help")

        tools_list.toggle_help(tool_id=self.FILTER_FAILED_TOOL_ID).wait_for_and_click()
        tools_list.tool_help(tool_id=self.FILTER_FAILED_TOOL_ID).wait_for_absent()

    @selenium_test
    def test_tool_discovery_open_tool_navigates_away(self):
        tools_list = self._open_tools_list_with_filter_failed()
        tools_list.open_tool_button(tool_id=self.FILTER_FAILED_TOOL_ID).wait_for_and_click()
        tools_list._.wait_for_absent()
        self.screenshot("tools_list_navigated_to_tool")

    @playwright_only("Validates /tools/list tag autocomplete behavior with Playwright backend.")
    @selenium_test
    def test_tools_list_tag_autocomplete_search(self):
        self.home()
        self.components.tool_panel.discover_tools_link.wait_for_and_click()

        tools_list = self.components.tools_list
        tools_list._.wait_for_visible()
        tools_list.search_input.wait_for_and_send_keys("tag:Get")

        autocomplete = self.page.locator('[data-description="search-autocomplete"]')
        autocomplete.wait_for(state="visible")

        suggestions = autocomplete.locator("button")
        suggestion_count = suggestions.count()
        matching_index = None
        for index in range(suggestion_count):
            if "Get Data" in (suggestions.nth(index).text_content() or ""):
                matching_index = index
                break

        assert matching_index is not None, "Expected Get Data autocomplete suggestion to be present."
        suggestions.nth(matching_index).click()

        search_input = self.page.locator('.tools-list [data-description="filter text input"]')
        self._wait_on(
            lambda: search_input.input_value().strip() == 'tag:"Get Data"',
            'tools/list search input to contain tag:"Get Data"',
        )

        tools_list.tool_card(tool_id="upload1").wait_for_visible()


class TestToolDiscoveryViewLoggedIn(SeleniumTestCase):
    """Test tool discovery view features that require login.

    Current it just verifies that the favorite tool button does not tell you
    to login unlike the anonymous case above. Actual exercise of the favorite
    feature would be great.
    """

    ensure_registered = True

    @selenium_test
    def test_favorite_tool_button_when_logged_in(self):
        """Test that the favorite tool button works for logged-in users."""
        # Navigate to tool discovery view
        self.home()
        self.components.tool_panel.discover_tools_link.wait_for_and_click()

        # Search for a tool
        tools_list = self.components.tools_list
        tools_list._.wait_for_visible()
        tools_list.search_input.wait_for_and_send_keys("filter failed")
        tools_list.tool_card(tool_id="__FILTER_FAILED_DATASETS__").wait_for_visible()

        # Verify favorite button is available (not showing login message)
        button = tools_list.favorite_tool_button(tool_id="__FILTER_FAILED_DATASETS__").wait_for_visible()
        # When logged in, the title should not be the login prompt
        title = button.get_attribute("title")
        assert title != "Login or Register to Favorite Tools"
