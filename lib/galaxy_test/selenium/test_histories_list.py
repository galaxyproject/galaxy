from selenium.webdriver.common.by import By

from .framework import (
    retry_assertion_during_transitions,
    selenium_only,
    selenium_test,
    SharedStateSeleniumTestCase,
)


class TestSavedHistories(SharedStateSeleniumTestCase):
    @selenium_only("Not yet migrated to support Playwright backend")
    @selenium_test
    def test_histories_list(self):
        self._login()
        self.navigate_to_histories_page()
        self.assert_histories_in_list([self.history2_name, self.history3_name])

    @selenium_only("Not yet migrated to support Playwright backend")
    @selenium_test
    def test_history_switch(self):
        self._login()
        self.navigate_to_histories_page()
        self.screenshot("histories_saved_grid")
        self.select_history_card_operation(self.history2_name, '[id^="g-card-action-switch-history-"]')
        self.sleep_for(self.wait_types.UX_RENDER)

        @retry_assertion_during_transitions
        def assert_history_name_switched():
            assert self.history_panel_name() == self.history2_name

        assert_history_name_switched()

    @selenium_only("Not yet migrated to support Playwright backend")
    @selenium_test
    def test_history_view(self):
        self._login()
        self.navigate_to_histories_page()
        self.select_history_card_operation(self.history2_name, '[id^="g-card-action-view-history-"]')
        history_name = self.wait_for_selector("[data-description='name display']")
        assert history_name.text == self.history2_name

    @selenium_only("Not yet migrated to support Playwright backend")
    @selenium_test
    def test_history_publish(self):
        self._login()
        self.navigate_to_histories_page()

        # Publish the history
        self.select_history_card_operation(self.history2_name, '[id^="g-card-action-share-access-management-history-"]')
        self.make_accessible_and_publishable()

        self.navigate_to_histories_page()
        self.components.histories.advanced_search_toggle.wait_for_and_click()
        self.check_advanced_search_filter("published")
        self.sleep_for(self.wait_types.UX_RENDER)

        self.assert_histories_in_list([self.history2_name])

    @selenium_only("Not yet migrated to support Playwright backend")
    @selenium_test
    def test_rename_history(self):
        self._login()
        self.navigate_to_histories_page()

        self.select_history_card_operation("Unnamed history", '[id^="g-card-rename-history-"]')

        # Rename the history
        history_name_input = self.wait_for_selector(".ui-form-element input.ui-input")
        history_name_input.clear()
        history_name_input.send_keys(self.history1_name)

        self.wait_for_and_click_selector("button#submit")

        self.navigate_to_histories_page()

        self.assert_histories_in_list([self.history1_name, self.history2_name, self.history3_name])

    @selenium_only("Not yet migrated to support Playwright backend")
    @selenium_test
    def test_delete_and_undelete_history(self):
        self._login()
        self.navigate_to_histories_page()

        # Delete the history
        self.select_history_card_operation(self.history2_name, '[id^="g-card-action-delete-history-"]', True)
        self.components.histories.delete_history_confirm.wait_for_and_click()

        self.sleep_for(self.wait_types.UX_RENDER)
        self.assert_histories_in_list([self.history2_name], False)

        self.components.histories.advanced_search_toggle.wait_for_and_click()
        self.check_advanced_search_filter("deleted")
        self.sleep_for(self.wait_types.UX_RENDER)

        # Restore the history
        self.select_history_card_operation(self.history2_name, '[id^="g-card-action-restore-history-"]')

        self.assert_histories_sorted_in_list([])
        self.components.histories.reset_input.wait_for_and_click()

        self.assert_histories_in_list([self.history2_name])

    @selenium_only("Not yet migrated to support Playwright backend")
    @selenium_test
    def test_permanently_delete_history(self):
        self._login()
        self.create_history(self.history4_name)

        self.navigate_to_histories_page()
        self.assert_histories_in_list([self.history4_name])

        self.select_history_card_operation(self.history4_name, '[id^="g-card-action-purge-history-"]', True)
        self.components.histories.delete_history_confirm.wait_for_and_click()

        self.sleep_for(self.wait_types.UX_RENDER)
        self.assert_histories_in_list([self.history4_name], False)

        self.components.histories.advanced_search_toggle.wait_for_and_click()
        self.check_advanced_search_filter("purged")
        self.sleep_for(self.wait_types.UX_RENDER)

        self.assert_histories_in_list([self.history4_name])

    @selenium_only("Not yet migrated to support Playwright backend")
    @selenium_test
    def test_delete_and_undelete_multiple_histories(self):
        self._login()
        self.navigate_to_histories_page()

        # Select multiple histories
        self.toggle_card_selection_in_list("#history-list", [self.history2_name, self.history3_name])

        # Delete multiple histories
        self.components.histories.bulk_delete_button.wait_for_and_click()
        self.components.histories.bulk_delete_confirm.wait_for_and_click()

        # Display deleted histories
        self.components.histories.advanced_search_toggle.wait_for_and_click()
        self.check_advanced_search_filter("deleted")

        # Select multiple histories
        self.sleep_for(self.wait_types.UX_RENDER)
        self.toggle_card_selection_in_list("#history-list", [self.history2_name, self.history3_name])

        # Restore multiple histories
        self.components.histories.bulk_restore_button.wait_for_and_click()
        self.components.histories.bulk_restore_confirm.wait_for_and_click()

        # Verify deleted histories have been restored
        self.components.histories.reset_input.wait_for_and_click()
        self.assert_histories_in_list([self.history2_name, self.history3_name])

    @selenium_only("Not yet migrated to support Playwright backend")
    @selenium_test
    def test_bulk_open_in_multiview(self):
        self._login()
        self.navigate_to_histories_page()

        # Select multiple histories
        self.toggle_card_selection_in_list("#history-list", [self.history2_name, self.history3_name])

        # Open selected histories in multiview
        self.components.histories.bulk_open_multiview_button.wait_for_and_click()

        # Wait for navigation to multiview page
        self.sleep_for(self.wait_types.UX_RENDER)

        # Verify we are on the multiview page
        assert "/histories/view_multiple" in self.current_url

        # Verify the selected histories are present in the multiview panel
        present_histories = self.components.multi_history_panel.histories.all()
        present_history_names = [self.get_history_name(history) for history in present_histories]
        assert set(present_history_names) == {self.history2_name, self.history3_name}

    @selenium_only("Not yet migrated to support Playwright backend")
    @selenium_test
    def test_bulk_open_in_multiview_limit_confirmation(self):
        self._login()

        # Create additional histories to exceed the limit (10 is the max)
        additional_histories = []
        for i in range(10 + 1):
            history_name = self._get_random_name()
            self.create_history(history_name)
            additional_histories.append(history_name)

        self.navigate_to_histories_page()

        # Select more than 10 histories (we'll select 11)
        all_histories_to_select = additional_histories
        self.toggle_card_selection_in_list("#history-list", all_histories_to_select)

        # Click the bulk open multiview button
        self.components.histories.bulk_open_multiview_button.wait_for_and_click()

        # Wait for the confirmation dialog to appear
        self.sleep_for(self.wait_types.UX_RENDER)

        # Verify the confirmation dialog is displayed
        confirm_dialog = self.wait_for_selector("#bulk-open-multiview-histories")
        assert confirm_dialog.is_displayed()

        # Verify the dialog contains information about the limit
        dialog_text = confirm_dialog.text
        assert "10" in dialog_text  # The maximum number of histories
        assert "11" in dialog_text  # The number of histories selected

        # Click confirm to proceed despite the limit
        self.wait_for_and_click(self.components.histories.bulk_open_multiview_limit_confirm_button)

        # Wait for dialog to close
        self.sleep_for(self.wait_types.UX_RENDER)

        # Verify we are on the multiview page
        assert "/histories/view_multiple" in self.current_url

        # Verify the maximum allowed histories are opened in multiview
        present_histories = self.components.multi_history_panel.histories.all()
        assert len(present_histories) == 10

    def get_history_name(self, history):
        history_name_element = history.find_element(By.CSS_SELECTOR, "[data-description='name display']")
        return history_name_element.text

    @selenium_only("Not yet migrated to support Playwright backend")
    @selenium_test
    def test_sort_by_name(self):
        self._login()
        self.navigate_to_histories_page()

        self.wait_for_and_click_selector('[data-title="Sort by name ascending"]')
        self.wait_for_and_click_selector('[data-title="Sort by name ascending"]')
        self.sleep_for(self.wait_types.UX_RENDER)

        expected_histories = [self.history2_name, self.history3_name]

        actual_histories = self.get_history_titles(len(expected_histories))

        if self.history1_name in actual_histories:
            expected_histories.append(self.history1_name)
        expected_histories = sorted(expected_histories)

        # Filter out histories created by other tests
        actual_histories = [x for x in actual_histories if x in self.all_histories]

        assert actual_histories == expected_histories

    @selenium_only("Not yet migrated to support Playwright backend")
    @selenium_test
    def test_standard_search(self):
        self._login()
        self.navigate_to_histories_page()
        self.components.histories.search_input.wait_for_and_send_keys(self.history2_name)
        self.assert_histories_sorted_in_list([self.history2_name])
        self.components.histories.reset_input.wait_for_and_click()
        self.components.histories.search_input.wait_for_and_send_keys(self.history4_name)
        self.assert_histories_sorted_in_list([])

    @selenium_only("Not yet migrated to support Playwright backend")
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
        actual_histories = self.get_history_titles(len(expected_histories))
        assert len(actual_histories) == len(expected_histories)

        assert actual_histories == expected_histories

    def get_present_histories(self):
        self.sleep_for(self.wait_types.UX_RENDER)
        return self.components.histories.history_cards.all()

    @selenium_only("Not yet migrated to support Playwright backend")
    @selenium_test
    def test_tags(self):
        self._login()
        self.navigate_to_histories_page()

        self.sleep_for(self.wait_types.UX_RENDER)

        # Insert a tag
        tags_cell = self.get_history_card(self.history2_name).find_element(By.CSS_SELECTOR, ".stateless-tags")
        self.add_tag(tags_cell, self.history2_tags[0])

        # Search by tag
        tag = tags_cell.find_element(By.CSS_SELECTOR, ".tag")
        tag.click()

        self.sleep_for(self.wait_types.UX_RENDER)

        self.assert_histories_sorted_in_list([self.history2_name], False)

    def _login(self):
        self.home()
        self.submit_login(self.user_email, retries=3)

    @retry_assertion_during_transitions
    def assert_histories_sorted_in_list(self, expected_histories, sort_matters=True):
        actual_histories = self.get_history_titles(len(expected_histories))
        if not sort_matters:
            actual_histories = set(actual_histories)
            expected_histories = set(expected_histories)
        assert actual_histories == expected_histories

    @retry_assertion_during_transitions
    def assert_histories_in_list(self, expected_histories, present=True):
        actual_histories = self.get_history_titles(len(expected_histories))
        intersection = set(actual_histories).intersection(expected_histories)
        if present:
            assert intersection == set(expected_histories)
        else:
            assert intersection == set()

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
