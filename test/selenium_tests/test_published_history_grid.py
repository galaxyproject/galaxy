import requests

from .framework import SeleniumTestCase, selenium_test


class HistoryGridTestCase(SeleniumTestCase):

    # @selenium_test
    # def test_history_grid_accessible(self):
    #     full_url = self.build_url('histories/list_published')
    #     response = requests.get(full_url)
    #     assert response.status_code == 200

    @selenium_test
    def test_history_grid_histories(self):
        self.setup_user_and_histories()
        self.navigate_to_published_histories_page()

        # Get Histories
        histories = []
        grid = self.wait_for_selector('#grid-table-body')
        for row in grid.find_elements_by_tag_name('tr'):
            cell = row.find_elements_by_tag_name('td')[0]  # Name
            histories.append(cell.text)

        assert histories == ['Second', 'First']

    def setup_user_and_histories(self):
        self.register()
        self.create_and_publish_history('First')
        self.create_and_publish_history('Second')

    def create_and_publish_history(self, name):
        self.click_history_options()  # Open history options menu

        create_history_link = self.driver.find_element_by_link_text(
            'Create New')
        create_history_link.click()

        # Rename the history
        editable_text_input_element = self.click_to_rename_history()
        editable_text_input_element.send_keys(name)
        self.send_enter(editable_text_input_element)
        self.publish_current_history()

    def publish_current_history(self):
        self.navigate_to_history_publish_page()
        with self.main_panel():
            selector = 'input[name="make_accessible_and_publish"]'
            publish_button = self.wait_for_selector(selector)
            publish_button.click()

    def navigate_to_history_publish_page(self):
        # self.click_history_option('Share or Publish')  # doesn't work!

        self.click_history_options()  # Open history options menu
        # publish_link = self.wait_for_selector('a[href^="/history/sharing"]')
        publish_link = self.driver.find_element_by_link_text('Share or Publish')
        publish_link.click()

    def navigate_to_published_histories_page(self):
        self.click_masthead_user()  # Open masthead menu
        self.click_label(
            self.navigation_data['labels']['masthead']['menus']['libraries'])
        selector = 'a[href="/histories/list_published"]'
        histories_link = self.wait_for_selector(selector)
        histories_link.click()

    def click_to_rename_history(self):
        self.history_panel_name_element().click()
        return self.wait_for_selector(self.edit_title_input_selector())

    def edit_title_input_selector(self):
        return self.test_data['historyPanel']['selectors']['history']['nameEditableTextInput']
