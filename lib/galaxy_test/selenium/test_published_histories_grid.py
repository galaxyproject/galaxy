from .framework import (
    retry_assertion_during_transitions,
    selenium_test,
    SharedStateSeleniumTestCase,
)


class HistoryGridTestCase(SharedStateSeleniumTestCase):
    @selenium_test
    def test_history_grid_histories(self):
        self.navigate_to_published_histories_page()
        self.assert_histories_in_grid(self.all_histories)

    @selenium_test
    def test_history_grid_search_standard(self):
        self.navigate_to_published_histories_page()
        self.screenshot("histories_published_grid")
        self.published_grid_search_for(self.history1_name)
        self.assert_grid_histories_are([self.history1_name])

        self.unset_filter("free-text-search", self.history1_name)
        self.published_grid_search_for(self.history4_name)

        self.assert_grid_histories_are([])

    @selenium_test
    def test_history_grid_search_advanced(self):
        self.navigate_to_published_histories_page()

        self.wait_for_and_click_selector("#standard-search .advanced-search-toggle")

        name_filter_selector = "#input-name-filter"
        annot_filter_selector = "#input-annotation-filter"
        owner_filter_selector = "#input-username-filter"
        tags_filter_selector = "#input-tags-filter"

        # Search by name
        self.set_filter(name_filter_selector, self.history1_name)
        self.screenshot("histories_published_grid_advanced")
        self.assert_grid_histories_are([self.history1_name])
        self.unset_filter("name", self.history1_name)

        self.set_filter(name_filter_selector, self.history4_name)
        self.assert_grid_histories_are([])
        self.unset_filter("name", self.history4_name)

        # Search by annotation
        self.set_filter(annot_filter_selector, self.history3_annot)
        self.assert_grid_histories_are([self.history3_name])
        self.unset_filter("annotation", self.history3_annot)

        # Search by owner
        owner = self.user2_email.split("@")[0]
        self.set_filter(owner_filter_selector, owner)
        self.assert_grid_histories_are([self.history2_name])
        self.unset_filter("username", owner)

        # Search by tags
        self.set_filter(tags_filter_selector, self.history1_tags[0])
        self.assert_grid_histories_are([self.history1_name, self.history3_name], False)
        self.unset_filter("tags", self.history1_tags[0])

    # Trying to address an intermittent failure by injecting a small rendering
    # sleep. to be honest, I'm not sure that the timing is the issue, because
    # this test never fails when run on its own, only when part of a longer test
    # run, but there's so few moving parts here, I'm not sure what else to try.
    @selenium_test
    def test_history_grid_sort_by_name(self):
        self.navigate_to_published_histories_page()
        self.sleep_for(self.wait_types.UX_RENDER)
        self.wait_for_and_click_selector("th#name-header > a")
        self.sleep_for(self.wait_types.UX_RENDER)
        self.assert_grid_histories_are(sorted(self.all_histories))

    @selenium_test
    def test_history_grid_sort_by_owner(self):
        self.navigate_to_published_histories_page()
        self.wait_for_and_click_selector("th#username-header > a")
        self.assert_grid_histories_sorted_by_owner()

    @selenium_test
    def test_history_grid_tag_click(self):
        self.navigate_to_published_histories_page()

        tags = None
        grid = self.wait_for_selector("#grid-table-body")
        for row in grid.find_elements_by_tag_name("tr"):
            td = row.find_elements_by_tag_name("td")
            name = td[0].text
            if name == self.history1_name:
                tags = td[4]
                break

        if tags is None:
            raise AssertionError(f"Failed to find history with name [{self.history1_name}]")

        tag_button_selector = "div.tag-name"
        tag_buttons = tags.find_elements_by_css_selector(tag_button_selector)
        tag_button_text = None
        target_tag_button_text = self.history1_tags[0]
        for tag_button in tag_buttons:
            tag_button_text = tag_button.text
            if tag_button_text == target_tag_button_text:
                break

        self.assertEqual(tag_button_text, target_tag_button_text)
        tag_button.click()

        self.assert_grid_histories_are([self.history1_name, self.history3_name], False)

    def get_histories(self, sleep=False):
        self.sleep_for(self.wait_types.UX_RENDER)
        names = []
        grid = self.wait_for_selector("#grid-table-body")
        for row in grid.find_elements_by_tag_name("tr"):
            cell = row.find_elements_by_tag_name("td")[0]  # Name
            names.append(cell.text)
        return names

    @retry_assertion_during_transitions
    def assert_grid_histories_sorted_by_owner(self):
        histories = self.get_histories()
        index_1, index_2, index_3 = (histories.index(n) for n in self.all_histories)
        # 1 and 3 are owned by a owner whose username lexicographically
        # precedes 2. So verify 1 and 3 come before 2.
        assert index_1 < index_2
        assert index_3 < index_2

    @retry_assertion_during_transitions
    def assert_grid_histories_are(self, expected_histories, sort_matters=True):
        actual_histories = self.get_histories()

        # Filter out histories created by other tests
        all_histories = self.all_histories + ["No items"]
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
        close_link_selector = f'a[filter_key="{filter_key}"][filter_val="{filter_value}"]'
        self.wait_for_and_click_selector(close_link_selector)
        self.sleep_for(self.wait_types.UX_RENDER)

    def setup_shared_state(self):
        tag1 = self._get_random_name(len=5)
        tag2 = self._get_random_name(len=5)
        tag3 = self._get_random_name(len=5)

        HistoryGridTestCase.user1_email = self._get_random_email("test1")
        HistoryGridTestCase.user2_email = self._get_random_email("test2")
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
        self.set_history_annotation(self.history3_annot)
        self.publish_current_history()
        self.logout_if_needed()

        self.register(self.user2_email)
        self.create_history(self.history2_name)
        self.history_panel_add_tags(self.history2_tags)
        self.publish_current_history()

    def create_history(self, name):
        self.home()
        self.history_panel_create_new_with_name(name)

    def publish_current_history(self):
        self.click_history_option_sharing()
        self.make_accessible_and_publishable()

    def navigate_to_published_histories_page(self):
        self.home()
        self.click_masthead_shared_data()
        self.components.masthead.published_histories.wait_for_and_click()
