import time

from .framework import SeleniumTestCase, selenium_test

# Test case data
HISTORY1_NAME = 'First'
HISTORY2_NAME = 'Second'
HISTORY3_NAME = 'Third'
HISTORY4_NAME = 'Four'


class SavedHistoriesTestCase(SeleniumTestCase):

    def setUp(self):
        super(SavedHistoriesTestCase, self).setUp()
        self.ensure_user_and_histories()

    @selenium_test
    def test_saved_histories_list(self):
        self.navigate_to_saved_histories_page()
        self.assert_histories_in_grid([HISTORY2_NAME, HISTORY3_NAME])

    @selenium_test
    def test_history_switch(self):
        self.navigate_to_saved_histories_page()

        self.click_popup_option(HISTORY2_NAME, 'Switch')
        time.sleep(1)
        history_name = self.history_panel_name_element()

        self.assertEqual(history_name.text, HISTORY2_NAME)

    @selenium_test
    def test_history_view(self):
        self.navigate_to_saved_histories_page()
        self.click_popup_option(HISTORY2_NAME, 'View')
        history_name = self.wait_for_selector('.name.editable-text')
        self.assertEqual(history_name.text, HISTORY2_NAME)

    @selenium_test
    def test_history_publish(self):
        self.navigate_to_saved_histories_page()

        # Publish the history
        self.click_popup_option(HISTORY2_NAME, 'Share or Publish')
        selector = 'input[name="make_accessible_and_publish"]'
        publish_button = self.wait_for_selector_clickable(selector)
        publish_button.click()

        self.navigate_to_saved_histories_page()

        self.show_advanced_search()
        self.select_filter('sharing', 'published')
        time.sleep(1)

        self.assert_grid_histories_are([HISTORY2_NAME])

    @selenium_test
    def test_rename_history(self):
        self.navigate_to_saved_histories_page()

        self.click_popup_option('Unnamed history', 'Rename')

        # Rename the history
        history_name_input = self.wait_for_selector('input[name="name"]')
        history_name_input.clear()
        history_name_input.send_keys(HISTORY1_NAME)
        self.send_enter(history_name_input)

        message = self.wait_for_selector_visible('.infomessagelarge')
        expected_message = 'History: Unnamed history renamed to: %s' % HISTORY1_NAME
        self.assertEqual(expected_message, message.text)

        self.navigate_to_saved_histories_page()
        self.assert_grid_histories_are([HISTORY1_NAME, HISTORY2_NAME, HISTORY3_NAME], False)

    @selenium_test
    def test_delete_and_undelete_history(self):
        self.navigate_to_saved_histories_page()

        # Delete the history
        self.click_popup_option(HISTORY2_NAME, 'Delete')

        self.assert_histories_in_grid([HISTORY2_NAME], False)

        self.show_advanced_search()
        self.select_filter('deleted', 'True')
        time.sleep(1)

        # Restore the history
        self.click_popup_option(HISTORY2_NAME, 'Undelete')

        self.wait_for_selector_visible('.donemessage')
        self.select_filter('deleted', 'False')

        self.assert_histories_in_grid([HISTORY2_NAME])

    @selenium_test
    def test_delete_and_undelete_multiple_histories(self):
        self.navigate_to_saved_histories_page()

        delete_button_selector = 'input[type="button"][value="Delete"]'
        undelete_button_selector = 'input[type="button"][value="Undelete"]'

        # Delete multiple histories
        self.check_histories([HISTORY2_NAME, HISTORY3_NAME])
        delete_button = self.wait_for_selector_clickable(delete_button_selector)
        delete_button.click()

        self.assert_histories_in_grid([HISTORY2_NAME, HISTORY3_NAME], False)

        self.show_advanced_search()
        self.select_filter('deleted', 'True')
        time.sleep(1)

        # Restore multiple histories
        self.check_histories([HISTORY2_NAME, HISTORY3_NAME])
        undelete_button = self.wait_for_selector_clickable(undelete_button_selector)
        undelete_button.click()

        self.wait_for_selector_visible('.donemessage')
        self.select_filter('deleted', 'False')

        self.assert_histories_in_grid([HISTORY2_NAME, HISTORY3_NAME])

    @selenium_test
    def test_sort_by_name(self):
        self.navigate_to_saved_histories_page()

        sort_link = self.wait_for_selector_clickable('.sort-link[sort_key="name"]')
        sort_link.click()

        actual_histories = self.get_histories()
        if 'Unnamed history' in actual_histories:
            expected_histories = [HISTORY2_NAME, HISTORY3_NAME, 'Unnamed history']
        else:
            expected_histories = [HISTORY1_NAME, HISTORY2_NAME, HISTORY3_NAME]

        self.assertEqual(actual_histories, expected_histories)

    @selenium_test
    def test_standard_search(self):
        self.navigate_to_saved_histories_page()

        input_selector = '#input-free-text-search-filter'
        search_input = self.wait_for_selector(input_selector)
        search_input.send_keys(HISTORY2_NAME)
        self.send_enter(search_input)

        self.assert_grid_histories_are([HISTORY2_NAME])

        self.unset_filter('free-text-search', HISTORY2_NAME)
        search_input = self.wait_for_selector(input_selector)
        search_input.send_keys(HISTORY4_NAME)
        self.send_enter(search_input)

        self.assert_grid_histories_are(['No Items'])

    def assert_grid_histories_are(self, expected_histories, sort_matters=True):
        actual_histories = self.get_histories()
        if not sort_matters:
            actual_histories = set(actual_histories)
            expected_histories = set(expected_histories)
        self.assertEqual(actual_histories, expected_histories)

    def assert_histories_in_grid(self, expected_histories, present=True):
        actual_histories = self.get_histories()
        intersection = list(set(actual_histories).intersection(expected_histories))
        if present:
            self.assertEqual(intersection, expected_histories)
        else:
            self.assertEqual(intersection, [])

    def get_histories(self):
        time.sleep(1.5)
        names = []
        grid = self.wait_for_selector('#grid-table-body')
        for row in grid.find_elements_by_tag_name('tr'):
            td = row.find_elements_by_tag_name('td')
            name = td[1].text if td[0].text == '' else td[0].text
            # name_cell = row.find_elements_by_tag_name('td')[1]
            names.append(name)
        return names

    def unset_filter(self, filter_key, filter_value):
        close_button_selector = 'a[filter_key="%s"][filter_val="%s"]' % \
            (filter_key, filter_value)
        close_button = self.wait_for_selector_clickable(close_button_selector)
        close_button.click()
        time.sleep(.5)

    def navigate_to_saved_histories_page(self):
        self.home()
        self.click_masthead_user()  # Open masthead menu

        label = self.navigation_data['labels']['masthead']['menus']['user']
        self.click_label(label)

        saved_histories_link = self.wait_for_selector_clickable('a[href="/histories/list"]')
        saved_histories_link.click()

    def ensure_user_and_histories(self):
        if getattr(SavedHistoriesTestCase, 'user_email', None):
            self.home()  # ensure Galaxy is loaded
            self.submit_login(self.user_email)
            return

        SavedHistoriesTestCase.user_email = self._get_random_email()
        self.register(self.user_email)
        self.create_history(HISTORY2_NAME)
        self.create_history(HISTORY3_NAME)

    def create_history(self, name):
        self.click_history_option('Create New')

        # Rename the history
        editable_text_input_element = self.click_to_rename_history()
        editable_text_input_element.send_keys(name)
        self.send_enter(editable_text_input_element)

    def show_advanced_search(self):
        search_selector = '#standard-search .advanced-search-toggle'
        search_link = self.wait_for_selector_clickable(search_selector)
        search_link.click()

    def select_filter(self, filter_key, filter_value):
        filter_selector = 'a[filter_key="%s"][filter_val="%s"]' % \
            (filter_key, filter_value)
        filter_link = self.wait_for_selector_clickable(filter_selector)
        filter_link.click()

    def click_history_option(self, option_label):
        self.home()
        self.click_history_options()  # Open history menu

        # Click labelled option
        menu_option = self.driver.find_element_by_link_text(option_label)
        menu_option.click()

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

        popup_menu_button = history_menu_button.find_element_by_css_selector('.popup')
        x_offset = popup_menu_button.size['width'] - 5
        y_offset = popup_menu_button.size['height'] - 5
        self.action_chains().move_to_element_with_offset(popup_menu_button, x_offset, y_offset).click().perform()

        popup_option = self.driver.find_element_by_link_text(option_label)
        popup_option.click()

    def check_histories(self, histories):
        grid = self.wait_for_selector('#grid-table-body')
        for row in grid.find_elements_by_tag_name('tr'):
            td = row.find_elements_by_tag_name('td')
            history_name = td[1].text
            if history_name in histories:
                checkbox = td[0].find_element_by_tag_name('input')
                checkbox.click()

    def click_to_rename_history(self):
        self.history_panel_name_element().click()
        edit_title_input_selector = self.test_data['historyPanel']['selectors']['history']['nameEditableTextInput']
        return self.wait_for_selector(edit_title_input_selector)
