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
    def test_enter_runs_the_selected_result(self):
        self.home()
        self.command_palette_open()
        self.command_palette_type("datatypes")
        self.command_palette_wait_for_option("Datatypes")
        # the first row is selected as the results land, so enter runs it
        self.send_enter()
        self.command_palette_wait_for_closed()
        self._wait_on(
            lambda: self.current_url.endswith("/datatypes"),
            "palette navigation result to route to the datatypes page",
            wait_type=self.wait_types.UX_TRANSITION,
        )
        self.wait_for_xpath_visible('//h1[text()="Datatypes"]')

    @selenium_test
    def test_category_narrows_the_fan_out(self):
        self.home()
        self.command_palette_open()
        self.command_palette_type("workflow")
        self.command_palette_wait_for_option("Workflows")
        # "All" fans every provider out, so the navigation entry arrives beside
        # the actions provider's own rows
        assert "Create workflow" in self.command_palette_option_titles()
        self.command_palette_click_category("navigation")
        self.command_palette_wait_for_option("Workflows")
        self.screenshot("command_palette_category_navigation")
        assert self.components.command_palette.category(category="navigation").has_class("active")
        self.components.command_palette.section(section="navigation").wait_for_visible()
        assert "Create workflow" not in self.command_palette_option_titles()

    @selenium_test
    def test_escape_steps_back_out_of_a_scope(self):
        self.home()
        self.command_palette_open()
        self.command_palette_type("t:")
        assert self.command_palette_badge_text() == "Tools"
        self.command_palette_type("cat")
        self.command_palette_wait_for_input_value("cat")
        # escape clears the text, then drops the badge, then closes
        self.send_escape()
        self.command_palette_wait_for_input_value("")
        assert self.command_palette_badge_text() == "Tools"
        self.send_escape()
        self.components.command_palette.badge.wait_for_absent_or_hidden()
        self.send_escape()
        self.command_palette_wait_for_closed()

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
    def test_help_applies_a_scope(self):
        self.home()
        self.command_palette_open()
        self.command_palette_type("?")
        self.command_palette_wait_for_option("Search tools")
        self.screenshot("command_palette_help")
        # the panel is a way into the scopes, not only a list of them
        self.command_palette_click_option("Search my histories")
        assert self.command_palette_badge_text() == "My histories"
