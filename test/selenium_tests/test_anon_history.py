from .framework import (
    selenium_test,
    SeleniumTestCase
)


class AnonymousHistoriesTestCase(SeleniumTestCase):

    @selenium_test
    def test_anon_history_landing(self):
        self.home()
        self.assert_initial_history_panel_state_correct()

        tag_icon_selector = self.navigation.history_panel.selectors.tag_icon
        annotation_icon_selector = self.navigation.history_panel.selectors.annotation_icon
        self.assert_absent_or_hidden(tag_icon_selector)
        self.assert_absent_or_hidden(annotation_icon_selector)

        # History has a name but...
        name_element = self.wait_for_present(self.navigation.history_panel.selectors.name)
        name_element.click()

        # ... name should NOT be editable when clicked by anon-user
        editable_text_class = self.navigation._.selectors.editable_text
        assert editable_text_class.as_css_class not in name_element.get_attribute("class")

    @selenium_test
    def test_anon_history_upload(self):
        self.home()
        self.perform_upload(self.get_filename("1.txt"))
        self.wait_for_history()
        hda = self.latest_history_item()
        self.home()
        element = self.wait_for_selector(self.hda_div_selector(hda["id"]))
        assert 'state-ok' in element.get_attribute("class")

        # empty should be NO LONGER be displayed
        self.assert_absent_or_hidden(self.navigation.history_panel.selectors.empty_message)

    @selenium_test
    def test_anon_history_after_registration(self):
        self._upload_file_anonymous_then_register_user()
        hda = self.latest_history_item()
        self.home()
        element = self.wait_for_selector(self.hda_div_selector(hda["id"]))
        assert 'state-ok' in element.get_attribute("class")

    @selenium_test
    def test_clean_anon_history_after_logout(self):
        self._upload_file_anonymous_then_register_user()
        self.logout_if_needed()
        # Give Galaxy a chance to load the new empty history for that now
        # anonymous user. Make sure this new history is empty.
        self.history_panel_wait_for_history_loaded()
        history_contents = self.current_history_contents()
        assert len(history_contents) == 0

    def _upload_file_anonymous_then_register_user(self):
        self.home()
        self.perform_upload(self.get_filename("1.txt"))
        self.wait_for_history()
        self.register()
