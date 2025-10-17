from .framework import (
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

    @selenium_test
    def test_tool_discovery_landing(self):
        """Test navigation to the tool discovery view."""
        # Navigate to home page
        self.home()

        # Access the tool discovery view via the "Discover Tools" link
        tool_panel = self.components.tool_panel
        tool_panel.discover_tools_link.wait_for_and_click()

        # Verify the tools list view is displayed
        tools_list = self.components.tools_list
        tools_list._.wait_for_visible()
        self.screenshot("tools_list_landing")

        tools_list.search_input.wait_for_and_send_keys("filter failed")

        # Verify the filtered tool card appears
        tools_list.tool_card(tool_id="__FILTER_FAILED_DATASETS__").wait_for_visible()
        self.screenshot("tools_list_filtered")

        # Click the version button to show version information
        tools_list.version_button(tool_id="__FILTER_FAILED_DATASETS__").wait_for_and_click()
        self.screenshot("tools_list_show_version")

        # Verify favorite button is available (not showing login message)
        button = tools_list.favorite_tool_button(tool_id="__FILTER_FAILED_DATASETS__").wait_for_visible()
        # When logged in, the title should not be the login prompt
        title = button.get_attribute("title")
        assert title == "Login or Register to Favorite Tools"

        # Verify help is initially hidden
        tools_list.tool_help(tool_id="__FILTER_FAILED_DATASETS__").assert_absent()

        # Toggle help to show it
        tools_list.toggle_help(tool_id="__FILTER_FAILED_DATASETS__").wait_for_and_click()
        tools_list.tool_help(tool_id="__FILTER_FAILED_DATASETS__").wait_for_visible()
        self.screenshot("tools_list_show_help")

        # Toggle help to hide it again
        tools_list.toggle_help(tool_id="__FILTER_FAILED_DATASETS__").wait_for_and_click()
        tools_list.tool_help(tool_id="__FILTER_FAILED_DATASETS__").wait_for_absent()

        # Click the open tool button to navigate to the tool
        tools_list.open_tool_button(tool_id="__FILTER_FAILED_DATASETS__").wait_for_and_click()

        # Verify we've left the tools list view and the tool form is displayed
        tools_list._.wait_for_absent()
        self.screenshot("tools_list_navigated_to_tool")


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
