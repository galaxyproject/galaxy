import time

# import requests

from .framework import SeleniumTestCase, selenium_test

# Test case data
USER1_EMAIL = 'test_user1@test.test'
USER2_EMAIL = 'test_user2@test.test'
HISTORY1_NAME = 'First'
HISTORY2_NAME = 'Second'


class HistoryGridTestCase(SeleniumTestCase):

    # def setUp(self):
    #     super(HistoryGridTestCase, self).setUp()

    # @selenium_test
    # def test_history_grid_accessible(self):
    #     full_url = self.build_url('histories/list_published')
    #     response = requests.get(full_url)
    #     assert response.status_code == 200

    @selenium_test
    def test_history_grid_histories(self):
        self.setup_users_and_histories()
        self.navigate_to_published_histories_page()
        histories = self.get_histories()
        assert histories == [HISTORY2_NAME, HISTORY1_NAME]

    @selenium_test
    def test_history_grid_standard_search(self):
        self.navigate_to_published_histories_page()

        input_selector = '#input-free-text-search-filter'
        search_input = self.wait_for_selector(input_selector)
        search_input.send_keys(HISTORY1_NAME)
        self.send_enter(search_input)

        histories = self.get_histories()
        assert histories == [HISTORY1_NAME]

    # @selenium_test
    # def test_history_grid_advanced_search(self):
    #     pass

    @selenium_test
    def test_history_grid_sort_by_name(self):
        self.navigate_to_published_histories_page()
        sort_link = self.wait_for_selector('th#name-header > a')
        sort_link.click()
        histories = self.get_histories()
        assert histories == [HISTORY1_NAME, HISTORY2_NAME]

    @selenium_test
    def test_history_grid_sort_by_owner(self):
        self.navigate_to_published_histories_page()
        sort_link = self.wait_for_selector('th#username-header > a')
        sort_link.click()
        histories = self.get_histories()
        assert histories == [HISTORY1_NAME, HISTORY2_NAME]

    def get_histories(self):
        time.sleep(1)

        names = []
        grid = self.wait_for_selector('#grid-table-body')
        for row in grid.find_elements_by_tag_name('tr'):
            cell = row.find_elements_by_tag_name('td')[0]  # Name
            names.append(cell.text)

        return names

    def setup_users_and_histories(self):
        self.register(USER1_EMAIL)
        self.create_and_publish_history(HISTORY1_NAME)
        self.logout_if_needed()
        self.register(USER2_EMAIL)
        self.create_and_publish_history(HISTORY2_NAME)

    def create_and_publish_history(self, name):
        self.click_history_option('Create New')

        # Rename the history
        editable_text_input_element = self.click_to_rename_history()
        editable_text_input_element.send_keys(name)
        self.send_enter(editable_text_input_element)
        self.publish_current_history()

    def publish_current_history(self):
        self.click_history_option('Share or Publish')
        with self.main_panel():
            selector = 'input[name="make_accessible_and_publish"]'
            publish_button = self.wait_for_selector(selector)
            publish_button.click()

    def navigate_to_published_histories_page(self):
        self.home()
        self.click_masthead_user()  # Open masthead menu
        self.click_label(
            self.navigation_data['labels']['masthead']['menus']['libraries'])
        selector = 'a[href="/histories/list_published"]'
        histories_link = self.wait_for_selector(selector)
        histories_link.click()

    def click_history_option(self, option_label):
        self.home()
        self.click_history_options()  # Open history menu

        # Click labelled option
        menu_option = self.driver.find_element_by_link_text(option_label)
        menu_option.click()

    def click_to_rename_history(self):
        self.history_panel_name_element().click()
        return self.wait_for_selector(self.edit_title_input_selector())

    def edit_title_input_selector(self):
        return self.test_data['historyPanel']['selectors']['history']['nameEditableTextInput']
