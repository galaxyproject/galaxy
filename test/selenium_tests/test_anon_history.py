from .framework import SeleniumTestCase
from .framework import selenium_test


class AnonymousHistoriesTestCase(SeleniumTestCase):

    @selenium_test
    def test_anon_history_landing(self):
        self.home()
        self.assert_initial_history_panel_state_correct()

        tag_icon_selector = self.test_data["historyPanel"]["selectors"]["history"]["tagIcon"]
        anno_icon_selector = self.test_data["historyPanel"]["selectors"]["history"]["annoIcon"]
        self.assert_selector_absent(tag_icon_selector)
        self.assert_selector_absent(anno_icon_selector)

        name_selector = self.test_data["historyPanel"]["selectors"]["history"]["name"]
        name_element = self.wait_for_selector(name_selector)

        # name should NOT be editable when clicked by anon-user
        editable_text_class = self.test_data["selectors"]["editableText"]
        assert editable_text_class not in name_element.get_attribute("class")
        name_element.click()

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
        empty_msg_selector = self.test_data["historyPanel"]["selectors"]["history"]["emptyMsg"]
        self.assert_selector_absent_or_hidden(empty_msg_selector)

    @selenium_test
    def test_anon_history_after_registration(self):
        self.home()
        self.perform_upload(self.get_filename("1.txt"))
        self.wait_for_history()
        self.register()
        hda = self.latest_history_item()
        self.home()
        element = self.wait_for_selector(self.hda_div_selector(hda["id"]))
        assert 'state-ok' in element.get_attribute("class")

    @selenium_test
    def test_clean_anon_history_after_logout(self):
        self.home()
        self.perform_upload(self.get_filename("1.txt"))
        self.wait_for_history()
        self.register()
        self.logout_if_needed()
        history_contents = self.current_history_contents()
        assert len(history_contents) == 0
