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

        table_elements = self.workflow_index_table_elements()
        assert len(table_elements) == 1

        new_workflow = table_elements[0].find_element(By.CSS_SELECTOR, ".workflow-dropdown")
        assert "TestWorkflow1 (imported from URL)" in new_workflow.text, new_workflow.text

    @selenium_test
    def test_view(self):
        self.workflow_index_open()
        self._workflow_import_from_url()
        self.workflow_index_click_option("View external link")
        assert self.driver.current_url == EXAMPLE_WORKFLOW_URL_1
        self.driver.back()
        self.components.workflows.external_link.wait_for_visible()
        # font-awesome title handling broken... https://github.com/FortAwesome/vue-fontawesome/issues/63
        # title_element = external_link_icon.find_element(By.TAG_NAME, "title")
        # assert EXAMPLE_WORKFLOW_URL_1 in title_element.text
        self.workflow_index_click_option("View")
        workflow_show = self.components.workflow_show
        title_item = self.components.workflow_show.title.wait_for_visible()
        assert "TestWorkflow1" in title_item.text
        import_link = workflow_show.import_link.wait_for_visible()
        assert "Import Workflow" in import_link.get_attribute("title")
        self.screenshot("workflow_manage_view")
        # TODO: Test display of steps...

    @selenium_test
    def test_rename(self):
        self.workflow_index_open()
        self._workflow_import_from_url()
        self.workflow_index_rename("CoolNewName")

        @retry_assertion_during_transitions
        def check_name():
            name = self.workflow_index_name()
            assert "CoolNewName" == name, name

        check_name()

    @selenium_test
    def test_download(self):
        self.workflow_index_open()
        self._workflow_import_from_url()
        # TODO: fill this test out - getting downloaded files in general through Selenium is a bit tough,
        # going through the motions though should catch a couple potential problems.
        self.workflow_index_click_option("Download")

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
        self.workflow_index_add_tag("mytag")
        self._workflow_import_from_url()
        self.workflow_index_add_tag("mytaglonger")
        self._workflow_import_from_url()

        self.workflow_index_search_for("mytag")
        self._assert_showing_n_workflows(3)
        self.screenshot("workflow_manage_search_by_tag_freetext")
        self.workflow_index_search_for("thisisnotatag")
        self._assert_showing_n_workflows(0)

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
        self.workflow_index_rename("searchforthis")
        self._assert_showing_n_workflows(1)
        self.screenshot("workflow_manage_search")

        self.workflow_index_search_for("doesnotmatch")
        self._assert_showing_n_workflows(0)

        self.workflow_index_search_for()
        self._assert_showing_n_workflows(1)

        self.workflow_index_search_for("searchforthis")
        self._assert_showing_n_workflows(1)

    @selenium_test
    def test_index_search_filters(self):
        self.workflow_index_open()
        self._workflow_import_from_url()
        self.workflow_index_rename("searchforthis")
        self._assert_showing_n_workflows(1)

        self.workflow_index_search_for("name:doesnotmatch")
        self._assert_showing_n_workflows(0)
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
        self._assert_showing_n_workflows(0)
        self.screenshot("workflow_manage_search_name_alias")

    @selenium_test
    def test_workflow_delete(self):
        self.workflow_index_open()
        self._workflow_import_from_url()
        self.workflow_index_rename("fordelete")
        self._assert_showing_n_workflows(1)
        self.workflow_index_click_option("Delete")
        self._assert_showing_n_workflows(0)

        self.workflow_index_open()
        self._assert_showing_n_workflows(0)

    @selenium_test
    def test_pagination(self):
        self.workflow_index_open()
        self._workflow_import_from_url()
        self.workflow_index_open()
        self._workflow_import_from_url()
        self.workflow_index_open()
        self._workflow_import_from_url()
        self.workflow_index_open()
        self._workflow_import_from_url()
        self.workflow_index_open()

        self._assert_showing_n_workflows(4)

        # by default the pager only appears when there are too many workflows
        # for one page - so verify it is absent and then swap to showing just
        # one workflow per page.
        workflows = self.components.workflows
        workflows.pager.wait_for_absent_or_hidden()
        self.re_get_with_query_params("rows_per_page=1")
        self._assert_showing_n_workflows(1)
        self.screenshot("workflows_paginated_first_page")
        self._assert_current_page_is(workflows, 1)
        self._next_page(workflows)
        self._assert_current_page_is(workflows, 2)
        self.screenshot("workflows_paginated_next_page")
        self._previous_page(workflows)
        self._assert_current_page_is(workflows, 1)
        self._last_page(workflows)
        self._assert_current_page_is(workflows, 4)
        self.screenshot("workflows_paginated_last_page")
        self._first_page(workflows)
        self._assert_current_page_is(workflows, 1)
