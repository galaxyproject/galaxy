from .framework import (
    retry_assertion_during_transitions,
    retry_during_transitions,
    selenium_test,
    SharedStateSeleniumTestCase,
)


class SavedHistoriesTestCase(SharedStateSeleniumTestCase):

    @selenium_test
    def test_saved_histories_list(self):
        self._login()
        self.navigate_to_saved_histories_page()
        self.assert_histories_in_grid([self.history2_name, self.history3_name])

    @selenium_test
    def test_history_switch(self):
        self._login()
        self.navigate_to_saved_histories_page()
        self.screenshot("histories_saved_grid")
        self.click_popup_option(self.history2_name, 'Switch')
        self.sleep_for(self.wait_types.UX_RENDER)

        @retry_assertion_during_transitions
        def assert_history_name_switched():
            self.assertEqual(self.history_panel_name(), self.history2_name)

        assert_history_name_switched()

    @selenium_test
    def test_history_view(self):
        self._login()
        self.navigate_to_saved_histories_page()
        self.click_popup_option(self.history2_name, 'View')
        history_name = self.wait_for_selector('.name.editable-text')
        self.assertEqual(history_name.text, self.history2_name)

    @selenium_test
    def test_history_publish(self):
        self._login()
        self.navigate_to_saved_histories_page()

        # Publish the history
        self.click_popup_option(self.history2_name, 'Share or Publish')
        self.components.histories.sharing.make_accessible_and_publish.wait_for_and_click()

        self.navigate_to_saved_histories_page()

        self.histories_click_advanced_search()
        self.select_filter('sharing', 'published')
        self.sleep_for(self.wait_types.UX_RENDER)

        self.assert_histories_in_grid([self.history2_name])

    @selenium_test
    def test_rename_history(self):
        self._login()
        self.navigate_to_saved_histories_page()

        self.click_popup_option('Unnamed history', 'Rename')

        # Rename the history
        history_name_input = self.wait_for_selector('.ui-form-element input.ui-input')
        history_name_input.clear()
        history_name_input.send_keys(self.history1_name)

        self.wait_for_and_click_selector("button#submit")

        self.navigate_to_saved_histories_page()

        self.assert_histories_in_grid([self.history1_name, self.history2_name, self.history3_name])

    @selenium_test
    def test_delete_and_undelete_history(self):
        self._login()
        self.navigate_to_saved_histories_page()

        # Delete the history
        self.click_popup_option(self.history2_name, 'Delete')

        self.assert_histories_in_grid([self.history2_name], False)

        self.histories_click_advanced_search()
        self.select_filter('deleted', 'True')
        self.sleep_for(self.wait_types.UX_RENDER)

        # Restore the history
        self.click_popup_option(self.history2_name, 'Undelete')

        self.assert_grid_histories_are([])
        self.select_filter('deleted', 'False')

        self.assert_histories_in_grid([self.history2_name])

    @selenium_test
    def test_permanently_delete_history(self):
        self._login()
        self.create_history(self.history4_name)

        self.navigate_to_saved_histories_page()
        self.assert_histories_in_grid([self.history4_name])

        self.click_popup_option(self.history4_name, 'Delete Permanently')
        alert = self.driver.switch_to.alert
        alert.accept()

        self.assert_histories_in_grid([self.history4_name], False)

        self.histories_click_advanced_search()
        self.select_filter('deleted', 'True')

        self.assert_histories_in_grid([self.history4_name])

    @selenium_test
    def test_delete_and_undelete_multiple_histories(self):
        self._login()
        self.navigate_to_saved_histories_page()

        delete_button_selector = 'input[type="button"][value="Delete"]'
        undelete_button_selector = 'input[type="button"][value="Undelete"]'

        # Delete multiple histories
        self.check_histories([self.history2_name, self.history3_name])
        self.wait_for_and_click_selector(delete_button_selector)

        self.assert_histories_in_grid([self.history2_name, self.history3_name], False)

        self.histories_click_advanced_search()
        self.select_filter('deleted', 'True')
        self.sleep_for(self.wait_types.UX_RENDER)

        # Restore multiple histories
        self.check_histories([self.history2_name, self.history3_name])
        self.wait_for_and_click_selector(undelete_button_selector)

        self.assert_grid_histories_are([])
        # Following msg popups but goes away and so can cause transient errors.
        # self.wait_for_selector_visible('.donemessage')
        self.select_filter('deleted', 'False')

        self.assert_histories_in_grid([self.history2_name, self.history3_name])

    @selenium_test
    def test_sort_by_name(self):
        self._login()
        self.navigate_to_saved_histories_page()

        self.wait_for_and_click_selector('.sort-link[sort_key="name"]')
        actual_histories = self.get_histories()

        expected_histories = [self.history2_name, self.history3_name]
        if self.history1_name in actual_histories:
            expected_histories.append(self.history1_name)
        expected_histories = sorted(expected_histories)

        # Filter out histories created by other tests
        actual_histories = [x for x in actual_histories if x in self.all_histories]

        self.assertEqual(actual_histories, expected_histories)

    @selenium_test
    def test_standard_search(self):
        self._login()
        self.navigate_to_saved_histories_page()

        input_selector = '#input-free-text-search-filter'
        search_input = self.wait_for_selector(input_selector)
        search_input.send_keys(self.history2_name)
        self.send_enter(search_input)

        self.assert_grid_histories_are([self.history2_name])

        self.unset_filter('free-text-search', self.history2_name)
        search_input = self.wait_for_selector(input_selector)
        search_input.send_keys(self.history4_name)
        self.send_enter(search_input)

        self.assert_grid_histories_are([])

    @selenium_test
    def test_advanced_search(self):
        self._login()
        self.navigate_to_saved_histories_page()

        self.histories_click_advanced_search()

        name_filter_selector = '#input-name-filter'
        tags_filter_selector = '#input-tags-filter'

        # Search by name
        self.set_filter(name_filter_selector, self.history2_name)
        self.assert_grid_histories_are([self.history2_name])
        self.unset_filter('name', self.history2_name)

        self.set_filter(name_filter_selector, self.history4_name)
        self.assert_grid_histories_are([])
        self.unset_filter('name', self.history4_name)

        # Search by tags
        self.set_filter(tags_filter_selector, self.history3_tags[0])
        self.assert_grid_histories_are([self.history3_name])
        self.unset_filter('tags', self.history3_tags[0])

        self.set_filter(tags_filter_selector, self.history4_tags[0])
        self.assert_grid_histories_are([])
        self.unset_filter('tags', self.history4_tags[0])

    @selenium_test
    def test_tags(self):
        self._login()
        self.navigate_to_saved_histories_page()

        # Click the add tag button
        tags_cell = self.get_history_tags_cell(self.history2_name)
        add_tag_button = tags_cell.find_element_by_css_selector('.add-tag-button')
        add_tag_button.click()

        # Insert a tag
        tags_cell = self.get_history_tags_cell(self.history2_name)
        tag_area = tags_cell.find_element_by_tag_name('textarea')
        tag_area.send_keys(self.history2_tags[0])
        self.send_enter(tag_area)

        # Search by tag
        tags_cell = self.get_history_tags_cell(self.history2_name)
        tag = tags_cell.find_element_by_css_selector('span.tag-name')
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
        self.assertEqual(actual_histories, expected_histories)

    @retry_assertion_during_transitions
    def assert_histories_in_grid(self, expected_histories, present=True):
        actual_histories = self.get_histories()
        intersection = set(actual_histories).intersection(expected_histories)
        if present:
            self.assertEqual(intersection, set(expected_histories))
        else:
            self.assertEqual(intersection, set())

    @retry_during_transitions
    def get_histories(self):
        self.sleep_for(self.wait_types.UX_RENDER)
        names = []
        grid = self.wait_for_selector('#grid-table-body')
        for row in grid.find_elements_by_tag_name('tr'):
            td = row.find_elements_by_tag_name('td')
            name = td[1].text if td[0].text == '' else td[0].text
            if name != "No Items":
                names.append(name)
        return names

    def set_filter(self, selector, value):
        filter_input = self.wait_for_selector_clickable(selector)
        filter_input.send_keys(value)
        self.send_enter(filter_input)

    def unset_filter(self, filter_key, filter_value):
        close_button_selector = 'a[filter_key="%s"][filter_val="%s"]' % \
            (filter_key, filter_value)
        self.wait_for_and_click_selector(close_button_selector)
        self.sleep_for(self.wait_types.UX_RENDER)

    def navigate_to_saved_histories_page(self):
        self.home()
        self.click_masthead_user()  # Open masthead menu
        self.components.masthead.saved_histories.wait_for_and_click()

    def setup_shared_state(self):
        SavedHistoriesTestCase.user_email = self._get_random_email()
        SavedHistoriesTestCase.history1_name = self._get_random_name()
        SavedHistoriesTestCase.history2_name = self._get_random_name()
        SavedHistoriesTestCase.history3_name = self._get_random_name()
        SavedHistoriesTestCase.history4_name = self._get_random_name()
        SavedHistoriesTestCase.history2_tags = [self._get_random_name(len=5)]
        SavedHistoriesTestCase.history3_tags = [self._get_random_name(len=5)]
        SavedHistoriesTestCase.history4_tags = [self._get_random_name(len=5)]
        SavedHistoriesTestCase.all_histories = [self.history1_name, self.history2_name, self.history3_name]

        self.register(self.user_email)
        self.create_history(self.history2_name)
        self.create_history(self.history3_name)
        self.history_panel_add_tags(self.history3_tags)

    def create_history(self, name):
        self.home()
        self.history_panel_create_new_with_name(name)

    def select_filter(self, filter_key, filter_value):
        filter_selector = 'a[filter_key="%s"][filter_val="%s"]' % \
            (filter_key, filter_value)
        self.wait_for_and_click_selector(filter_selector)

    def click_popup_option(self, history_name, option_label):
        history_menu_button = None
        grid = self.wait_for_selector('#grid-table-body')
        for row in grid.find_elements_by_tag_name('tr'):
            name_cell = row.find_elements_by_tag_name('td')[1]
            if name_cell.text == history_name:
                history_menu_button = name_cell
                break

        if history_menu_button is None:
            raise AssertionError('Failed to find history with name [%s]' % history_name)

        popup_menu_button = history_menu_button.find_element_by_css_selector('.dropdown-toggle')
        popup_menu_button.click()
        popup_option = self.driver.find_element_by_link_text(option_label)
        popup_option.click()

    def get_history_tags_cell(self, history_name):
        tags_cell = None
        grid = self.wait_for_selector('#grid-table-body')
        for row in grid.find_elements_by_tag_name('tr'):
            td = row.find_elements_by_tag_name('td')
            if td[1].text == history_name:
                tags_cell = td[4]
                break

        if tags_cell is None:
            raise AssertionError('Failed to find history with name [%s]' % history_name)

        return tags_cell

    def check_histories(self, histories):
        grid = self.wait_for_selector('#grid-table-body')
        for row in grid.find_elements_by_tag_name('tr'):
            td = row.find_elements_by_tag_name('td')
            history_name = td[1].text
            if history_name in histories:
                checkbox = td[0].find_element_by_tag_name('input')
                checkbox.click()
