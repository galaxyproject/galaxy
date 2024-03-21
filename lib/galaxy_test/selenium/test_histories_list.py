from selenium.webdriver.common.by import By

from .framework import (
    retry_assertion_during_transitions,
    selenium_test,
    SharedStateSeleniumTestCase,
)


class TestSavedHistories(SharedStateSeleniumTestCase):
    @selenium_test
    def test_histories_list(self):
        self._login()
        self.navigate_to_histories_page()
        self.assert_histories_in_grid([self.history2_name, self.history3_name])

    @selenium_test
    def test_history_switch(self):
        self._login()
        self.navigate_to_histories_page()
        self.screenshot("histories_saved_grid")
        self.select_grid_operation(self.history2_name, "Switch")
        self.sleep_for(self.wait_types.UX_RENDER)

        @retry_assertion_during_transitions
        def assert_history_name_switched():
            assert self.history_panel_name() == self.history2_name

        assert_history_name_switched()

    @selenium_test
    def test_history_view(self):
        self._login()
        self.navigate_to_histories_page()
        self.select_grid_operation(self.history2_name, "View")
        history_name = self.wait_for_selector("[data-description='name display']")
        assert history_name.text == self.history2_name

    @selenium_test
    def test_history_publish(self):
        self._login()
        self.navigate_to_histories_page()

        # Publish the history
        self.select_grid_operation(self.history2_name, "Share and Publish")
        self.make_accessible_and_publishable()

        self.navigate_to_histories_page()
        self.components.histories.advanced_search_toggle.wait_for_and_click()
        self.check_advanced_search_filter("published")
        self.sleep_for(self.wait_types.UX_RENDER)

        self.assert_histories_in_grid([self.history2_name])

    @selenium_test
    def test_rename_history(self):
        self._login()
        self.navigate_to_histories_page()

        self.select_grid_operation("Unnamed history", "Rename")

        # Rename the history
        history_name_input = self.wait_for_selector(".ui-form-element input.ui-input")
        history_name_input.clear()
        history_name_input.send_keys(self.history1_name)

        self.wait_for_and_click_selector("button#submit")

        self.navigate_to_histories_page()

        self.assert_histories_in_grid([self.history1_name, self.history2_name, self.history3_name])

    @selenium_test
    def test_delete_and_undelete_history(self):
        self._login()
        self.navigate_to_histories_page()

        # Delete the history
        self.select_grid_operation(self.history2_name, "Delete")
        alert = self.driver.switch_to.alert
        alert.accept()

        self.sleep_for(self.wait_types.UX_RENDER)
        self.assert_histories_in_grid([self.history2_name], False)

        self.components.histories.advanced_search_toggle.wait_for_and_click()
        self.check_advanced_search_filter("deleted")
        self.sleep_for(self.wait_types.UX_RENDER)

        # Restore the history
        self.select_grid_operation(self.history2_name, "Restore")

        self.assert_grid_histories_are([])
        self.components.histories.reset_input.wait_for_and_click()

        self.assert_histories_in_grid([self.history2_name])

    @selenium_test
    def test_permanently_delete_history(self):
        self._login()
        self.create_history(self.history4_name)

        self.navigate_to_histories_page()
        self.assert_histories_in_grid([self.history4_name])

        self.select_grid_operation(self.history4_name, "Delete Permanently")
        alert = self.driver.switch_to.alert
        alert.accept()

        self.sleep_for(self.wait_types.UX_RENDER)
        self.assert_histories_in_grid([self.history4_name], False)

        self.components.histories.advanced_search_toggle.wait_for_and_click()
        self.check_advanced_search_filter("purged")
        self.sleep_for(self.wait_types.UX_RENDER)

        self.assert_histories_in_grid([self.history4_name])

    @selenium_test
    def test_delete_and_undelete_multiple_histories(self):
        self._login()
        self.navigate_to_histories_page()

        delete_button_selector = 'button[data-description="grid batch delete"]'
        undelete_button_selector = 'button[data-description="grid batch restore"]'

        # Select multiple histories
        self.check_grid_rows("#histories-grid", [self.history2_name, self.history3_name])

        # Delete multiple histories
        self.wait_for_and_click_selector(delete_button_selector)
        alert = self.driver.switch_to.alert
        alert.accept()

        # Display deleted histories
        self.components.histories.advanced_search_toggle.wait_for_and_click()
        self.check_advanced_search_filter("deleted")

        # Select multiple histories
        self.sleep_for(self.wait_types.UX_RENDER)
        self.check_grid_rows("#histories-grid", [self.history2_name, self.history3_name])

        # Undelete multiple histories
        self.wait_for_and_click_selector(undelete_button_selector)
        alert = self.driver.switch_to.alert
        alert.accept()

        # Verify deleted histories have been undeleted
        self.components.histories.reset_input.wait_for_and_click()
        self.assert_histories_in_grid([self.history2_name, self.history3_name])

    @selenium_test
    def test_sort_by_name(self):
        self._login()
        self.navigate_to_histories_page()

        self.wait_for_and_click_selector('[data-description="grid sort key name"]')
        actual_histories = self.get_histories()

        expected_histories = [self.history2_name, self.history3_name]
        if self.history1_name in actual_histories:
            expected_histories.append(self.history1_name)
        expected_histories = sorted(expected_histories)

        # Filter out histories created by other tests
        actual_histories = [x for x in actual_histories if x in self.all_histories]

        assert actual_histories == expected_histories

    @selenium_test
    def test_standard_search(self):
        self._login()
        self.navigate_to_histories_page()
        self.components.histories.search_input.wait_for_and_send_keys(self.history2_name)
        self.assert_grid_histories_are([self.history2_name])
        self.components.histories.reset_input.wait_for_and_click()
        self.components.histories.search_input.wait_for_and_send_keys(self.history4_name)
        self.assert_grid_histories_are([])

    @selenium_test
    def test_advanced_search(self):
        self._login()
        self.navigate_to_histories_page()
        # search by name
        self.components.histories.advanced_search_toggle.wait_for_and_click()
        self.components.histories.advanced_search_name_input.wait_for_and_send_keys(self.history3_name)
        self.assert_histories_present([self.history3_name])

        self.components.histories.reset_input.wait_for_and_click()

        self.components.histories.advanced_search_name_input.wait_for_and_send_keys(self.history2_name)
        self.assert_histories_present([self.history2_name])

        self.components.histories.reset_input.wait_for_and_click()

        self.components.histories.advanced_search_name_input.wait_for_and_send_keys(self.history4_name)
        self.assert_histories_present([])

        self.components.histories.reset_input.wait_for_and_click()

        # search by tags
        self.components.histories.advanced_search_tag_area.wait_for_and_click()
        input_element = self.components.histories.advanced_search_tag_input.wait_for_visible()
        input_element.send_keys(self.history3_tags[0])
        self.send_enter(input_element)
        self.sleep_for(self.wait_types.UX_RENDER)
        self.assert_histories_present([self.history3_name])

    @retry_assertion_during_transitions
    def assert_histories_present(self, expected_histories, sort_by_matters=False):
        present_histories = self.get_present_histories()
        assert len(present_histories) == len(expected_histories)
        name_column = 1
        for index, row in enumerate(present_histories):
            cell = row.find_elements(By.TAG_NAME, "td")[name_column]
            if not sort_by_matters:
                assert cell.text in expected_histories
            else:
                assert cell.text == expected_histories[index]

    def get_present_histories(self):
        self.sleep_for(self.wait_types.UX_RENDER)
        return self.components.histories.histories.all()

    @selenium_test
    def test_tags(self):
        self._login()
        self.navigate_to_histories_page()

        # Insert a tag
        tag_column = 4
        tags_cell = self.select_grid_cell("#histories-grid", self.history2_name, tag_column)
        self.add_tag(tags_cell, self.history2_tags[0])

        # Search by tag
        tags_cell = self.select_grid_cell("#histories-grid", self.history2_name, tag_column)
        tag = tags_cell.find_element(By.CSS_SELECTOR, ".tag")
        tag.click()

        self.assert_grid_histories_are([self.history2_name], False)

    def _login(self):
        self.home()
        self.submit_login(self.user_email, retries=3)

    @retry_assertion_during_transitions
    def assert_grid_histories_are(self, expected_histories, sort_matters=True):
        actual_histories = self.get_histories()
        if not sort_matters:
            actual_histories = set(actual_histories)
            expected_histories = set(expected_histories)
        assert actual_histories == expected_histories

    @retry_assertion_during_transitions
    def assert_histories_in_grid(self, expected_histories, present=True):
        actual_histories = self.get_histories()
        intersection = set(actual_histories).intersection(expected_histories)
        if present:
            assert intersection == set(expected_histories)
        else:
            assert intersection == set()

    def get_histories(self):
        return self.get_grid_entry_names("#histories-grid")

    def add_tag(self, tags_cell, tag):
        tag_button = tags_cell.find_element(By.CSS_SELECTOR, ".stateless-tags button")
        tag_button.click()
        tag_input = tags_cell.find_element(By.CSS_SELECTOR, ".stateless-tags input")
        tag_input.send_keys(tag)
        self.send_enter(tag_input)
        self.send_escape(tag_input)
        self.sleep_for(self.wait_types.UX_RENDER)

    def setup_shared_state(self):
        TestSavedHistories.user_email = self._get_random_email()
        TestSavedHistories.history1_name = self._get_random_name()
        TestSavedHistories.history2_name = self._get_random_name()
        TestSavedHistories.history3_name = self._get_random_name()
        TestSavedHistories.history4_name = self._get_random_name()
        TestSavedHistories.history2_tags = [self._get_random_name(len=5)]
        TestSavedHistories.history3_tags = [self._get_random_name(len=5)]
        TestSavedHistories.history4_tags = [self._get_random_name(len=5)]
        TestSavedHistories.all_histories = [self.history1_name, self.history2_name, self.history3_name]

        self.register(self.user_email)
        self.create_history(self.history2_name)
        self.create_history(self.history3_name)
        self.history_panel_add_tags(self.history3_tags)

    def create_history(self, name):
        self.home()
        self.history_panel_create_new_with_name(name)
