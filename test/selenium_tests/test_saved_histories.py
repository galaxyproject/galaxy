import time

from .framework import SeleniumTestCase, selenium_test

# Test case data
HISTORY1_NAME = 'First'
HISTORY2_NAME = 'Second'


class SavedHistoriesTestCase(SeleniumTestCase):

    def setUp(self):
        super(SavedHistoriesTestCase, self).setUp()
        self.ensure_user_and_histories()

    @selenium_test
    def test_saved_histories_list(self):
        self.navigate_to_saved_histories_page()
        # self.assert_grid_histories_are([HISTORY2_NAME, 'Unnamed history'])
        histories = self.get_histories()
        assert HISTORY2_NAME in histories

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
        self.assert_grid_histories_are([HISTORY1_NAME, HISTORY2_NAME], False)

    def assert_grid_histories_are(self, expected_histories, sort_matters=True):
        actual_histories = self.get_histories()
        if not sort_matters:
            expected_histories = set(expected_histories)
            actual_histories = set(actual_histories)
        self.assertEqual(expected_histories, actual_histories)

    def get_histories(self):
        time.sleep(1.5)
        names = []
        grid = self.wait_for_selector('#grid-table-body')
        for row in grid.find_elements_by_tag_name('tr'):
            cell = row.find_elements_by_tag_name('td')[1]  # Name
            names.append(cell.text)
        return names

    def navigate_to_saved_histories_page(self):
        self.home()
        self.click_masthead_user()  # Open masthead menu

        label = self.navigation_data['labels']['masthead']['menus']['user']
        self.click_label(label)

        selector = 'a[href="/histories/list"]'
        histories_link = self.wait_for_selector_clickable(selector)
        histories_link.click()

    def ensure_user_and_histories(self):
        if getattr(SavedHistoriesTestCase, 'user_email', None):
            self.home()  # ensure Galaxy is loaded
            self.submit_login(self.user_email)
            return

        SavedHistoriesTestCase.user_email = self._get_random_email()
        self.register(self.user_email)
        self.create_history(HISTORY2_NAME)

    def create_history(self, name):
        self.click_history_option('Create New')

        # Rename the history
        editable_text_input_element = self.click_to_rename_history()
        editable_text_input_element.send_keys(name)
        self.send_enter(editable_text_input_element)

    def click_history_option(self, option_label):
        self.home()
        self.click_history_options()  # Open history menu

        # Click labelled option
        menu_option = self.driver.find_element_by_link_text(option_label)
        menu_option.click()

    def click_popup_option(self, history_name, option_label):
        # Find history with a given name
        history = None
        grid = self.wait_for_selector('#grid-table-body')
        for row in grid.find_elements_by_tag_name('tr'):
            name_cell = row.find_elements_by_tag_name('td')[1]
            if name_cell.text == history_name:
                history = name_cell
                break
        self.assertIsNotNone(history)

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
