from selenium.webdriver.common.by import By

from .framework import (
    EXAMPLE_WORKFLOW_URL_1,
    retry_assertion_during_transitions,
    selenium_test,
    SeleniumTestCase,
    TestsGalaxyPagers,
    UsesWorkflowAssertions,
)


class TestWorkflowManagement(SeleniumTestCase, TestsGalaxyPagers, UsesWorkflowAssertions):
    ensure_registered = True

    @selenium_test
    def test_import_from_url(self):
        self.workflow_index_open()
        self._workflow_import_from_url()

        workflow_cards = self.workflow_card_elements()
        assert len(workflow_cards) == 1

        first_workflow_card = workflow_cards[0].find_element(By.CSS_SELECTOR, '[id^="g-card-title-"] a')
        assert "TestWorkflow1 (imported from URL)" in first_workflow_card.text, first_workflow_card.text

    @selenium_test
    def test_import_accessibility(self):
        self.workflow_index_open()
        self.workflow_index_click_import()
        workflows = self.components.workflows
        workflows.import_file.assert_no_axe_violations_with_impact_of_at_least("moderate")
        workflows.import_trs_search_link.wait_for_and_click()
        # moderate violation relating to header ordering
        workflows.import_trs_search.assert_no_axe_violations_with_impact_of_at_least("serious")
        workflows.import_trs_id_link.wait_for_and_click()
        # ditto - moderate violation relating to header ordering
        workflows.import_trs_id.assert_no_axe_violations_with_impact_of_at_least("serious")

    @selenium_test
    def test_view(self):
        self.workflow_index_open()
        self._workflow_import_from_url()
        self.workflow_index_view_external_link()
        self.driver.switch_to.window(self.driver.window_handles[1])
        assert self.driver.current_url == EXAMPLE_WORKFLOW_URL_1
        self.driver.close()
        self.driver.switch_to.window(self.driver.window_handles[0])
        self.components.workflows.external_link.wait_for_visible()

        self.components.workflows.view_button.wait_for_and_click()

        workflow_preview = self.components.workflows.workflow_preview_container.wait_for_visible()
        assert "TestWorkflow1" in workflow_preview.text

    @selenium_test
    def test_rename(self):
        self.workflow_index_open()
        self._workflow_import_from_url()
        self.workflow_rename("CoolNewName")

        @retry_assertion_during_transitions
        def check_name():
            name = self.workflow_index_name()
            assert "CoolNewName" == name, name

        check_name()

    @selenium_test
    def test_workflow_index_accessibility(self):
        self.workflow_index_open()
        index_table = self.components.workflows.workflows_list
        # The selenium_test decorator will check for critical axe violations,
        # this test will be more rigorous but test only a specific component.
        index_table.assert_no_axe_violations_with_impact_of_at_least("critical")

    @selenium_test
    def test_download(self):
        self.workflow_index_open()
        self._workflow_import_from_url()
        # TODO: fill this test out - getting downloaded files in general through Selenium is a bit tough,
        # going through the motions though should catch a couple potential problems.
        self.components.workflows.download_button.wait_for_and_click()

    @selenium_test
    def test_tagging(self):
        self.workflow_index_open()
        self._workflow_import_from_url()

        self.workflow_index_add_tag("cooltag")

        @retry_assertion_during_transitions
        def check_tags():
            assert self.workflow_index_tags() == ["cooltag"]

        check_tags()
        self.screenshot("workflow_manage_tags")

    @selenium_test
    def test_tag_filtering(self):
        self.workflow_index_open()
        self._workflow_import_from_url()
        self.workflow_index_add_tag("mytag")
        self._workflow_import_from_url()
        self.workflow_index_open()
        self.workflow_index_add_tag("mytag")
        self._workflow_import_from_url()
        self.workflow_index_open()
        self.workflow_index_add_tag("mytaglonger")
        self._workflow_import_from_url()
        self.workflow_index_open()

        self.workflow_index_search_for("mytag")
        self._assert_showing_n_workflows(3)
        self.screenshot("workflow_manage_search_by_tag_freetext")
        self.workflow_index_search_for("thisisnotatag")
        self.components.workflows.workflow_not_found_message.wait_for_visible()

        self.workflow_index_search_for()
        self._assert_showing_n_workflows(4)

        self.workflow_index_click_tag("mytag", workflow_index=3)
        self._assert_showing_n_workflows(2)
        self.screenshot("workflow_manage_search_by_tag_exact")

        self.workflow_index_search_for()
        self._assert_showing_n_workflows(4)
        self.workflow_index_search_for("MyTaG")

    @selenium_test
    def test_index_search(self):
        self.workflow_index_open()
        self._workflow_import_from_url()
        self.workflow_rename("searchforthis")
        self._assert_showing_n_workflows(1)
        self.screenshot("workflow_manage_search")

        self.workflow_index_search_for("doesnotmatch")
        self.components.workflows.workflow_not_found_message.wait_for_visible()

        self.workflow_index_search_for()
        self._assert_showing_n_workflows(1)

        self.workflow_index_search_for("searchforthis")
        self._assert_showing_n_workflows(1)

    @selenium_test
    def test_index_search_filters(self):
        self.workflow_index_open()
        self._workflow_import_from_url()
        self.workflow_rename("searchforthis")
        self._assert_showing_n_workflows(1)

        self.workflow_index_search_for("name:doesnotmatch")
        self.components.workflows.workflow_not_found_message.wait_for_visible()
        self.screenshot("workflow_manage_search_no_matches")

        self.workflow_index_search_for()
        self._assert_showing_n_workflows(1)

        self.workflow_index_search_for("name:searchforthis")
        self._assert_showing_n_workflows(1)
        self.screenshot("workflow_manage_search_name_filter")

        self.workflow_index_search_for("n:searchforthis")
        self._assert_showing_n_workflows(1)
        self.screenshot("workflow_manage_search_name_alias")

        self.workflow_index_search_for("n:doesnotmatch")
        self.components.workflows.workflow_not_found_message.wait_for_visible()
        self.screenshot("workflow_manage_search_name_alias")

    @selenium_test
    def test_index_advanced_search(self):
        self.workflow_index_open()
        self._workflow_import_from_url()
        self.workflow_rename("searchforthis")
        self._assert_showing_n_workflows(1)

        self.workflow_index_add_tag("mytag")
        self.components.workflows.advanced_search_toggle.wait_for_and_click()
        # search by tag and name
        self.components.workflows.advanced_search_name_input.wait_for_and_send_keys("searchforthis")
        self.components.workflows.advanced_search_tag_input.wait_for_and_click()
        self.tagging_add(["mytag"])
        self._assert_showing_n_workflows(1)
        curr_value = self.workflow_index_get_current_filter()
        assert curr_value == "name:searchforthis tag:mytag", curr_value

        # clear filter
        self.components.workflows.clear_filter.wait_for_and_click()
        curr_value = self.workflow_index_get_current_filter()
        assert curr_value == "", curr_value

        # search by 2 tags, one of which is not present
        self.components.workflows.advanced_search_tag_input.wait_for_and_click()
        self.tagging_add(["'mytag'", "'DNEtag'"])
        curr_value = self.workflow_index_get_current_filter()
        assert curr_value == "tag:'mytag' tag:'DNEtag'", curr_value
        self.components.workflows.workflow_not_found_message.wait_for_visible()

    @selenium_test
    def test_workflow_delete(self):
        self.workflow_index_open()
        self._workflow_import_from_url()
        self.workflow_rename("fordelete")
        self._assert_showing_n_workflows(1)
        self.workflow_delete_by_name("fordelete")
        self.components.workflows.workflow_not_found_message.wait_for_visible()

        self.workflow_index_open()
        self.components.workflows.workflows_list_empty.wait_for_visible()
