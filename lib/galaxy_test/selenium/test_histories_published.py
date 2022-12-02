from selenium.webdriver.common.by import By

from .framework import (
    retry_assertion_during_transitions,
    selenium_test,
    SharedStateSeleniumTestCase,
)


class TestPublishedHistories(SharedStateSeleniumTestCase):
    @selenium_test
    def test_published_histories(self):
        self._login()
        self.navigate_to_published_histories()
        expected_history_names = self.get_published_history_names_from_server()
        self.assert_histories_present(expected_history_names)

    @selenium_test
    def test_published_histories_sort_by_name(self):
        self._login()
        self.navigate_to_published_histories()
        self.components.published_histories.column_header(column_number=1).wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)
        sorted_histories = self.get_published_history_names_from_server(sort_by="name")
        self.assert_histories_present(sorted_histories, sort_by_matters=True)

    @selenium_test
    def test_published_histories_sort_by_last_update(self):
        self._login()
        self.navigate_to_published_histories()
        self.components.published_histories.column_header(column_number=5).wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)
        expected_history_names = self.get_published_history_names_from_server(sort_by="update_time")
        self.assert_histories_present(expected_history_names, sort_by_matters=True)

    @selenium_test
    def test_published_histories_tag_click(self):
        self._login()
        self.navigate_to_published_histories()
        present_histories = self.get_present_histories()
        for row in present_histories:
            his = row.find_elements(By.TAG_NAME, "td")[0]
            if self.history3_name in his.text:
                row.find_elements(By.TAG_NAME, "td")[3].find_elements(By.CLASS_NAME, "tag-name")[0].click()
                break
        self.sleep_for(self.wait_types.UX_RENDER)
        self.assert_histories_present([self.history3_name, self.history1_name])

    @selenium_test
    def test_published_histories_search_standard(self):
        self._login()
        self.navigate_to_published_histories()
        self.components.published_histories.search_input.wait_for_and_send_keys(self.history1_name)
        self.sleep_for(self.wait_types.UX_RENDER)
        self.assert_histories_present([self.history1_name])

    @selenium_test
    def test_published_histories_search_advanced(self):
        self._login()
        self.navigate_to_published_histories()
        self.components.published_histories.advanced_search_toggle.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)
        # search by tag and name
        self.components.published_histories.advanced_search_tag_input.wait_for_and_send_keys(self.history3_tags)
        self.components.published_histories.advanced_search_name_input.wait_for_and_send_keys(self.history3_name)
        self.components.published_histories.advanced_search_submit.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)
        self.assert_histories_present([self.history3_name])

    @retry_assertion_during_transitions
    def assert_histories_present(self, expected_histories, sort_by_matters=False):
        present_histories = self.get_present_histories()
        assert len(present_histories) == len(expected_histories)
        for index, row in enumerate(present_histories):
            cell = row.find_elements(By.TAG_NAME, "td")[0]
            if not sort_by_matters:
                assert cell.text in expected_histories
            else:
                assert cell.text == expected_histories[index]

    def get_published_history_names_from_server(self, sort_by=None):
        published_histories = self.dataset_populator._get("histories/published").json()
        if sort_by:
            published_histories = sorted(published_histories, key=lambda x: x[sort_by])
        all_published_history_names = []
        for his in published_histories:
            all_published_history_names.append(his["name"])
        return all_published_history_names

    def get_present_histories(self):
        self.sleep_for(self.wait_types.UX_RENDER)
        return self.components.published_histories.histories.all()

    def navigate_to_published_histories(self):
        self.home()
        self.click_masthead_shared_data()
        self.components.masthead.published_histories.wait_for_and_click()

    def create_history(self, name):
        self.home()
        self.history_panel_create_new_with_name(name)

    def publish_current_history(self):
        self.click_history_option_sharing()
        self.make_accessible_and_publishable()

    def _login(self):
        self.home()
        self.submit_login(self.user1_email, retries=3)

    def setup_shared_state(self):
        tag1 = self._get_random_name(len=5)
        tag2 = self._get_random_name(len=5)
        tag3 = self._get_random_name(len=5)

        TestPublishedHistories.user1_email = self._get_random_email("test1")
        TestPublishedHistories.user2_email = self._get_random_email("test2")
        TestPublishedHistories.history1_name = self._get_random_name()
        TestPublishedHistories.history2_name = self._get_random_name()
        TestPublishedHistories.history3_name = self._get_random_name()
        TestPublishedHistories.history4_name = self._get_random_name()
        TestPublishedHistories.history1_tags = [tag1, tag2]
        TestPublishedHistories.history2_tags = [tag3]
        TestPublishedHistories.history3_tags = [tag1]
        TestPublishedHistories.history3_annot = self._get_random_name()

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
