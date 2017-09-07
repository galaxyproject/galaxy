import time

from .framework import SeleniumTestCase, selenium_test

# Test case data
HISTORY1_NAME = 'First'
HISTORY2_NAME = 'Second'
HISTORY3_NAME = 'Third'


class SavedHistoriesTestCase(SeleniumTestCase):

    def setUp(self):
        super(SavedHistoriesTestCase, self).setUp()
        self.ensure_user_and_histories()

    @selenium_test
    def test_saved_histories_list(self):
        self.navigate_to_saved_histories_page()
        # self.assert_grid_histories_are([HISTORY3_NAME, HISTORY2_NAME, 'Unnamed history'])
        self.assert_history_in_grid(HISTORY2_NAME)

    @selenium_test
    def test_history_switch(self):
        self.navigate_to_saved_histories_page()

        self.click_popup_option(HISTORY2_NAME, 'Switch')
        time.sleep(1)

        selector = '#current-history-panel .name.editable-text'
        history_name = self.wait_for_selector(selector)

        self.assertEqual(history_name.text, HISTORY2_NAME)

    @selenium_test
    def test_history_view(self):
        self.navigate_to_saved_histories_page()
        self.click_popup_option(HISTORY2_NAME, 'View')
        history_name = self.wait_for_selector('.name.editable-text')
        self.assertEqual(history_name.text, HISTORY2_NAME)

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

        self.assert_history_in_grid(HISTORY2_NAME, False)

        self.show_advanced_search()
        self.select_filter('deleted', 'True')
        time.sleep(1)

        # Restore the history
        self.click_popup_option(HISTORY2_NAME, 'Undelete')
        self.wait_for_selector_visible('.donemessage')
        self.select_filter('deleted', 'False')

        self.assert_history_in_grid(HISTORY2_NAME)

    def assert_grid_histories_are(self, expected_histories, sort_matters=True):
        actual_histories = self.get_histories()
        if not sort_matters:
            expected_histories = set(expected_histories)
            actual_histories = set(actual_histories)
        self.assertEqual(expected_histories, actual_histories)

    def assert_history_in_grid(self, history, present=True):
        histories = self.get_histories()
        if present:
            assert history in histories
        else:
            assert history not in histories

    def get_histories(self):
        time.sleep(1.5)
        names = []
        grid = self.wait_for_selector('#grid-table-body')
        for row in grid.find_elements_by_tag_name('tr'):
            name_cell = row.find_elements_by_tag_name('td')[1]
            names.append(name_cell.text)
        return names

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
        history = None
        grid = self.wait_for_selector('#grid-table-body')
        for row in grid.find_elements_by_tag_name('tr'):
            name_cell = row.find_elements_by_tag_name('td')[1]
            if name_cell.text == history_name:
                history = name_cell
                break

        if history is None:
            raise AssertionError('Failed to find history with name [%s]' % history_name)

        menu_button = name_cell.find_element_by_css_selector('.popup')
        x_offset = menu_button.size['width'] - 5
        y_offset = menu_button.size['height'] - 5
        self.action_chains().move_to_element_with_offset(menu_button, x_offset, y_offset).click().perform()

        popup_option = self.driver.find_element_by_link_text(option_label)
        popup_option.click()

    def click_to_rename_history(self):
        self.history_panel_name_element().click()
        edit_title_input_selector = self.test_data['historyPanel']['selectors']['history']['nameEditableTextInput']
        return self.wait_for_selector(edit_title_input_selector)
