import time

from .framework import SeleniumTestCase, selenium_test

# Test case data
HISTORY1_NAME = 'First'
HISTORY2_NAME = 'Second'
HISTORY3_NAME = 'Third'
HISTORY4_NAME = 'Four'
HISTORY1_TAGS = ['tag1', 'tag2']
HISTORY2_TAGS = ['tag3']
HISTORY3_TAGS = ['tag1']
HISTORY3_ANNOT = 'some description'


class HistoryGridTestCase(SeleniumTestCase):

    def setUp(self):
        super(HistoryGridTestCase, self).setUp()
        self.ensure_users_and_histories()

    @selenium_test
    def test_history_grid_histories(self):
        self.navigate_to_published_histories_page()
        self.assert_grid_histories_are([HISTORY2_NAME, HISTORY3_NAME, HISTORY1_NAME])

    @selenium_test
    def test_history_grid_search_standard(self):
        self.navigate_to_published_histories_page()

        input_selector = '#input-free-text-search-filter'
        search_input = self.wait_for_selector(input_selector)
        search_input.send_keys(HISTORY1_NAME)
        self.send_enter(search_input)
        self.assert_grid_histories_are([HISTORY1_NAME])

        self.unset_filter('free-text-search', HISTORY1_NAME)
        search_input = self.wait_for_selector(input_selector)
        search_input.send_keys(HISTORY4_NAME)
        self.send_enter(search_input)
        self.assert_grid_histories_are(['No Items'])

    @selenium_test
    def test_history_grid_search_advanced(self):
        self.navigate_to_published_histories_page()

        advanced_search_selector = '#standard-search .advanced-search-toggle'
        advanced_search_link = self.wait_for_selector(advanced_search_selector)
        advanced_search_link.click()

        name_filter_selector = '#input-name-filter'
        annot_filter_selector = '#input-annotation-filter'
        owner_filter_selector = '#input-username-filter'
        tags_filter_selector = '#input-tags-filter'

        # Search by name
        self.set_filter(name_filter_selector, HISTORY1_NAME)
        self.assert_grid_histories_are([HISTORY1_NAME])
        self.unset_filter('name', HISTORY1_NAME)

        # Search by annotation
        annotation = HISTORY3_ANNOT.split(' ')[0]
        self.set_filter(annot_filter_selector, annotation)
        self.assert_grid_histories_are([HISTORY3_NAME])
        self.unset_filter('annotation', annotation)

        # Search by owner
        owner = self.user2_email.split('@')[0]
        self.set_filter(owner_filter_selector, owner)
        self.assert_grid_histories_are([HISTORY2_NAME])
        self.unset_filter('username', owner)

        # Search by tags
        self.set_filter(tags_filter_selector, HISTORY1_TAGS[0])
        self.assert_grid_histories_are([HISTORY3_NAME, HISTORY1_NAME])
        self.unset_filter('tags', HISTORY1_TAGS[0])

    @selenium_test
    def test_history_grid_sort_by_name(self):
        self.navigate_to_published_histories_page()
        sort_link = self.wait_for_selector('th#name-header > a')
        sort_link.click()
        self.assert_grid_histories_are([HISTORY1_NAME, HISTORY2_NAME, HISTORY3_NAME])

    @selenium_test
    def test_history_grid_sort_by_owner(self):
        self.navigate_to_published_histories_page()
        sort_link = self.wait_for_selector('th#username-header > a')
        sort_link.click()
        self.assert_grid_histories_are([HISTORY1_NAME, HISTORY3_NAME, HISTORY2_NAME])

    @selenium_test
    def test_history_grid_tag_click(self):
        self.navigate_to_published_histories_page()

        tags = None
        grid = self.wait_for_selector('#grid-table-body')
        for row in grid.find_elements_by_tag_name('tr'):
            cell = row.find_elements_by_tag_name('td')[0]  # Name
            if cell.text == HISTORY1_NAME:
                tags = row.find_elements_by_tag_name('td')[4]  # Tags
                break
        assert tags is not None

        tag_button_selector = '.tag-area > .tag-button:first-child > .tag-name'
        tag_button = tags.find_element_by_css_selector(tag_button_selector)
        assert tag_button.text == HISTORY1_TAGS[0]

        tag_button.click()

        self.assert_grid_histories_are([HISTORY3_NAME, HISTORY1_NAME])

    def get_histories(self, sleep=False):
        time.sleep(1.5)

        names = []
        grid = self.wait_for_selector('#grid-table-body')
        for row in grid.find_elements_by_tag_name('tr'):
            cell = row.find_elements_by_tag_name('td')[0]  # Name
            names.append(cell.text)

        return names

    def assert_grid_histories_are(self, expected_histories, sort_matters=True):
        actual_histories = self.get_histories()
        if not sort_matters:
            expected_histories = set(expected_histories)
            actual_histories = set(actual_histories)

        self.assertEqual(expected_histories, actual_histories)

    def set_filter(self, selector, value):
        filter_input = self.wait_for_selector_clickable(selector)
        filter_input.send_keys(value)
        self.send_enter(filter_input)

    def unset_filter(self, filter_key, filter_value):
        close_link_selector = 'a[filter_key="%s"][filter_val="%s"]' % \
            (filter_key, filter_value)
        close_link = self.wait_for_selector_clickable(close_link_selector)
        close_link.click()
        time.sleep(.5)

    def set_tags(self, tags):
        tag_icon_selector = self.test_data['historyPanel']['selectors']['history']['tagIcon']
        tag_area_selector = self.test_data['historyPanel']['selectors']['history']['tagArea']

        if not self.is_displayed(tag_area_selector):
            tag_icon = self.wait_for_selector_clickable(tag_icon_selector)
            tag_icon.click()

        tag_area_selector += ' .tags-input input'
        tag_area = self.wait_for_selector_clickable(tag_area_selector)
        tag_area.click()

        for tag in tags:
            tag_area.send_keys(tag)
            self.send_enter(tag_area)
            time.sleep(.5)

    def set_annotation(self, annotation):
        anno_icon_selector = self.test_data['historyPanel']['selectors']['history']['annoIcon']
        anno_area_selector = self.test_data['historyPanel']['selectors']['history']['annoArea']

        if not self.is_displayed(anno_area_selector):
            annon_icon = self.wait_for_selector_clickable(anno_icon_selector)
            annon_icon.click()

        anno_area_selector += ' .annotation'
        annon_area = self.wait_for_selector_clickable(anno_area_selector)
        annon_area.click()

        area_editable_selector = anno_area_selector + ' textarea'
        done_button_selector = anno_area_selector + ' button'
        annon_area_editable = self.wait_for_selector_clickable(area_editable_selector)
        anno_done_button = self.wait_for_selector_clickable(done_button_selector)

        annon_area_editable.click()
        annon_area_editable.send_keys(annotation)
        anno_done_button.click()

    def ensure_users_and_histories(self):
        if getattr(HistoryGridTestCase, "user1_email", None):
            return

        HistoryGridTestCase.user1_email = self._get_random_email()
        HistoryGridTestCase.user2_email = self._get_random_email()
        self.register(self.user1_email)
        self.create_history(HISTORY1_NAME)
        self.set_tags(HISTORY1_TAGS)
        self.publish_current_history()

        self.create_history(HISTORY3_NAME)
        self.set_tags(HISTORY3_TAGS)
        self.set_annotation(HISTORY3_ANNOT)
        self.publish_current_history()
        self.logout_if_needed()

        self.register(self.user2_email)
        self.create_history(HISTORY2_NAME)
        self.set_tags(HISTORY2_TAGS)
        self.publish_current_history()

    def create_history(self, name):
        self.click_history_option('Create New')

        # Rename the history
        editable_text_input_element = self.click_to_rename_history()
        editable_text_input_element.send_keys(name)
        self.send_enter(editable_text_input_element)

    def publish_current_history(self):
        self.click_history_option('Share or Publish')
        with self.main_panel():
            selector = 'input[name="make_accessible_and_publish"]'
            publish_button = self.wait_for_selector_clickable(selector)
            publish_button.click()

    def navigate_to_published_histories_page(self):
        self.home()
        self.click_masthead_user()  # Open masthead menu
        self.click_label(
            self.navigation_data['labels']['masthead']['menus']['libraries'])
        selector = 'a[href="/histories/list_published"]'
        histories_link = self.wait_for_selector_clickable(selector)
        histories_link.click()

    def click_history_option(self, option_label):
        self.home()
        self.click_history_options()  # Open history menu

        # Click labelled option
        menu_option = self.driver.find_element_by_link_text(option_label)
        menu_option.click()

    def click_to_rename_history(self):
        self.history_panel_name_element().click()
        edit_title_input_selector = self.test_data['historyPanel']['selectors']['history']['nameEditableTextInput']
        return self.wait_for_selector(edit_title_input_selector)

    def is_displayed(self, selector):
        element = self.driver.find_element_by_css_selector(selector)
        return element.is_displayed()
