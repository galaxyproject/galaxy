import time

from .framework import (
    retry_assertion_during_transitions,
    selenium_test,
    SharedStateSeleniumTestCase,
)


class HistoryGridTestCase(SharedStateSeleniumTestCase):

    def setUp(self):
        super(HistoryGridTestCase, self).setUp()
        self.home()

    @selenium_test
    def test_history_grid_histories(self):
        self.navigate_to_published_histories_page()
        self.assert_histories_in_grid(self.all_histories)

    @selenium_test
    def test_history_grid_search_standard(self):
        self.navigate_to_published_histories_page()

        input_selector = '#input-free-text-search-filter'
        search_input = self.wait_for_selector(input_selector)
        search_input.send_keys(self.history1_name)
        self.send_enter(search_input)

        self.assert_grid_histories_are([self.history1_name])

        self.unset_filter('free-text-search', self.history1_name)
        search_input = self.wait_for_selector(input_selector)
        search_input.send_keys(self.history4_name)
        self.send_enter(search_input)

        self.assert_grid_histories_are(['No Items'])

    @selenium_test
    def test_history_grid_search_advanced(self):
        self.navigate_to_published_histories_page()

        self.wait_for_and_click_selector('#standard-search .advanced-search-toggle')

        name_filter_selector = '#input-name-filter'
        annot_filter_selector = '#input-annotation-filter'
        owner_filter_selector = '#input-username-filter'
        tags_filter_selector = '#input-tags-filter'

        # Search by name
        self.set_filter(name_filter_selector, self.history1_name)
        self.assert_grid_histories_are([self.history1_name])
        self.unset_filter('name', self.history1_name)

        self.set_filter(name_filter_selector, self.history4_name)
        self.assert_grid_histories_are(['No Items'])
        self.unset_filter('name', self.history4_name)

        # Search by annotation
        self.set_filter(annot_filter_selector, self.history3_annot)
        self.assert_grid_histories_are([self.history3_name])
        self.unset_filter('annotation', self.history3_annot)

        # Search by owner
        owner = self.user2_email.split('@')[0]
        self.set_filter(owner_filter_selector, owner)
        self.assert_grid_histories_are([self.history2_name])
        self.unset_filter('username', owner)

        # Search by tags
        self.set_filter(tags_filter_selector, self.history1_tags[0])
        self.assert_grid_histories_are([self.history1_name, self.history3_name], False)
        self.unset_filter('tags', self.history1_tags[0])

    @selenium_test
    def test_history_grid_sort_by_name(self):
        self.navigate_to_published_histories_page()
        self.wait_for_and_click_selector('th#name-header > a')
        self.assert_grid_histories_are(sorted(self.all_histories))

    @selenium_test
    def test_history_grid_sort_by_owner(self):
        self.navigate_to_published_histories_page()
        self.wait_for_and_click_selector('th#username-header > a')
        self.assert_grid_histories_sorted_by_owner()

    @selenium_test
    def test_history_grid_tag_click(self):
        self.navigate_to_published_histories_page()

        tags = None
        grid = self.wait_for_selector('#grid-table-body')
        for row in grid.find_elements_by_tag_name('tr'):
            td = row.find_elements_by_tag_name('td')
            name = td[0].text
            if name == self.history1_name:
                tags = td[4]
                break

        if tags is None:
            raise AssertionError('Failed to find history with name [%s]' % self.history1_name)

        tag_button_selector = '.tag-area > .tag-button:first-child > .tag-name'
        tag_button = tags.find_element_by_css_selector(tag_button_selector)
        self.assertEqual(tag_button.text, self.history1_tags[0])
        tag_button.click()

        self.assert_grid_histories_are([self.history1_name, self.history3_name], False)

    def get_histories(self, sleep=False):
        time.sleep(1.5)
        names = []
        grid = self.wait_for_selector('#grid-table-body')
        for row in grid.find_elements_by_tag_name('tr'):
            cell = row.find_elements_by_tag_name('td')[0]  # Name
            names.append(cell.text)
        return names

    @retry_assertion_during_transitions
    def assert_grid_histories_sorted_by_owner(self):
        histories = self.get_histories()
        index_1, index_2, index_3 = [histories.index(n) for n in self.all_histories]
        # 1 and 3 are owned by a owner whose username lexicographically
        # precedes 2. So verify 1 and 3 come before 2.
        assert index_1 < index_2
        assert index_3 < index_2

    @retry_assertion_during_transitions
    def assert_grid_histories_are(self, expected_histories, sort_matters=True):
        actual_histories = self.get_histories()

        # Filter out histories created by other tests
        all_histories = self.all_histories + ['No Items']
        actual_histories = [x for x in actual_histories if x in all_histories]

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

    def set_annotation(self, annotation):
        anno_icon_selector = self.test_data['historyPanel']['selectors']['history']['annoIcon']
        anno_area_selector = self.test_data['historyPanel']['selectors']['history']['annoArea']

        if not self.selector_is_displayed(anno_area_selector):
            self.wait_for_and_click_selector(anno_icon_selector)

        anno_area_selector += ' .annotation'
        self.wait_for_and_click_selector(anno_area_selector)

        area_editable_selector = anno_area_selector + ' textarea'
        done_button_selector = anno_area_selector + ' button'
        annon_area_editable = self.wait_for_selector_clickable(area_editable_selector)
        anno_done_button = self.wait_for_selector_clickable(done_button_selector)

        annon_area_editable.click()
        annon_area_editable.send_keys(annotation)
        anno_done_button.click()

    def setup_shared_state(self):
        tag1 = self._get_random_name(len=5)
        tag2 = self._get_random_name(len=5)
        tag3 = self._get_random_name(len=5)

        HistoryGridTestCase.user1_email = self._get_random_email('test1')
        HistoryGridTestCase.user2_email = self._get_random_email('test2')
        HistoryGridTestCase.history1_name = self._get_random_name()
        HistoryGridTestCase.history2_name = self._get_random_name()
        HistoryGridTestCase.history3_name = self._get_random_name()
        HistoryGridTestCase.history4_name = self._get_random_name()
        HistoryGridTestCase.history1_tags = [tag1, tag2]
        HistoryGridTestCase.history2_tags = [tag3]
        HistoryGridTestCase.history3_tags = [tag1]
        HistoryGridTestCase.history3_annot = self._get_random_name()
        HistoryGridTestCase.all_histories = [self.history1_name, self.history2_name, self.history3_name]

        self.register(self.user1_email)
        self.create_history(self.history1_name)
        self.history_panel_add_tags(self.history1_tags)
        self.publish_current_history()

        self.create_history(self.history3_name)
        self.history_panel_add_tags(self.history3_tags)
        self.set_annotation(self.history3_annot)
        self.publish_current_history()
        self.logout_if_needed()

        self.register(self.user2_email)
        self.create_history(self.history2_name)
        self.history_panel_add_tags(self.history2_tags)
        self.publish_current_history()

    def create_history(self, name):
        self.home()
        self.click_history_option('Create New')
        self.history_panel_rename(name)

    def publish_current_history(self):
        self.click_history_option('Share or Publish')
        with self.main_panel():
            selector = 'input[name="make_accessible_and_publish"]'
            publish_button = self.wait_for_selector_clickable(selector)
            publish_button.click()

            self.wait_for_selector_clickable('input[name="disable_link_access_and_unpublish"]')

    def navigate_to_published_histories_page(self):
        self.home()
        self.click_masthead_user()  # Open masthead menu
        self.click_label(
            self.navigation_data['labels']['masthead']['menus']['libraries'])
        selector = 'a[href="/histories/list_published"]'
        self.wait_for_and_click_selector(selector)
