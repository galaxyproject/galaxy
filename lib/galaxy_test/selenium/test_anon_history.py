from .framework import (
    selenium_test,
    SeleniumTestCase
)


class AnonymousHistoriesTestCase(SeleniumTestCase):

    @selenium_test
    def test_anon_history_landing(self):
        self.home()
        self.assert_initial_history_panel_state_correct()

        # Anonymous users can annotate or tag, these components should be absent.
        self.components.history_panel.tag_icon.assert_absent_or_hidden()
        self.components.history_panel.annotation_icon.assert_absent_or_hidden()

        # History has a name but...
        name_element = self.components.history_panel.name.wait_for_and_click()

        # ... name should NOT be editable when clicked by anon-user
        editable_text_class = self.navigation._.selectors.editable_text
        assert editable_text_class.as_css_class not in name_element.get_attribute("class")

    @selenium_test
    def test_anon_history_upload(self):
        self.home()
        self.perform_upload(self.get_filename("1.txt"))
        self.wait_for_history()
        # Reload the history and make sure the state is preserved.
        self.home()
        self.history_panel_wait_for_hid_state(1, "ok")

        # empty should be NO LONGER be displayed
        self.components.history_panel.empty_message.assert_absent_or_hidden()

    @selenium_test
    def test_anon_history_after_registration(self):
        self._upload_file_anonymous_then_register_user()
        self.home()
        self.history_panel_wait_for_hid_state(1, "ok")

    @selenium_test
    def test_clean_anon_history_after_logout(self):
        self._upload_file_anonymous_then_register_user()
        self.logout_if_needed()
        # Give Galaxy the chance to load a new empty history for that now
        # anonymous user. Make sure this new history is empty.
        self.home()
        self.history_panel_wait_for_history_loaded()
        history_contents = self.current_history_contents()
        assert len(history_contents) == 0

    def _upload_file_anonymous_then_register_user(self):
        self.home()
        self.perform_upload(self.get_filename("1.txt"))
        self.wait_for_history()
        self.register()
