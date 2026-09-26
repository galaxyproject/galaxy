from .framework import (
    managed_history,
    selenium_test,
    SeleniumTestCase,
)


class TestCommandPalette(SeleniumTestCase):
    ensure_registered = True

    @selenium_test
    def test_masthead_button_opens_palette(self):
        self.home()
        self.command_palette_open()
        # an empty palette still offers its default rows
        self.components.command_palette.option.wait_for_element_count_of_at_least(1)
        self.screenshot("command_palette_open")
        self.send_escape()
        self.command_palette_wait_for_closed()

    @selenium_test
    def test_shortcut_toggles_palette(self):
        self.home()
        self.command_palette_toggle_with_shortcut()
        self.command_palette_wait_for_open()
        self.command_palette_toggle_with_shortcut()
        self.command_palette_wait_for_closed()

    @selenium_test
    def test_navigation_result_opens_route(self):
        self.home()
        self.command_palette_open()
        self.command_palette_type("datatypes")
        self.command_palette_click_option("Datatypes")
        self.command_palette_wait_for_closed()
        self._wait_on(
            lambda: self.current_url.endswith("/datatypes"),
            "palette navigation result to route to the datatypes page",
            wait_type=self.wait_types.UX_TRANSITION,
        )

    @selenium_test
    def test_category_narrows_the_fan_out(self):
        self.home()
        self.command_palette_open()
        self.command_palette_type("workflow")
        self.command_palette_wait_for_option("Workflows")
        # "All" fans every provider out - the navigation entry and the sample
        # tools named after workflows both match, so there is something to narrow
        self.components.command_palette.sections.wait_for_element_count_of_at_least(2)
        self.command_palette_click_category("navigation")
        self.command_palette_wait_for_option("Workflows")
        self.screenshot("command_palette_category_navigation")
        assert self.components.command_palette.category(category="navigation").has_class("active")
        assert self.command_palette_section_count() == 1

    @selenium_test
    @managed_history
    def test_history_scope_finds_current_history(self):
        history_name = self.history_panel_name()
        self.command_palette_open()
        self.command_palette_type("h:")
        assert self.command_palette_badge_text() == "My histories"
        self.command_palette_type(history_name)
        self.command_palette_wait_for_option(history_name)
        self.screenshot("command_palette_history_scope")

    @selenium_test
    def test_help_lists_the_scopes(self):
        self.home()
        self.command_palette_open()
        self.command_palette_type("?")
        self.command_palette_wait_for_option("Search tools")
        self.screenshot("command_palette_help")
        # a scope the current user may not use is left out of the panel entirely
        assert "Search my histories" in self.command_palette_option_titles()
