from galaxy_test.base.populators import skip_if_github_down
from .framework import (
    retry_assertion_during_transitions,
    selenium_test,
    SeleniumTestCase,
)


class WorkflowManagementTestCase(SeleniumTestCase):

    ensure_registered = True

    @selenium_test
    def test_import_from_url(self):
        self.workflow_index_open()
        self._workflow_import_from_url()

        table_elements = self.workflow_index_table_elements()
        assert len(table_elements) == 1

        new_workflow = table_elements[0].find_element_by_css_selector(".workflow-dropdown")
        assert 'TestWorkflow1 (imported from uploaded file)' in new_workflow.text, new_workflow.text

    @selenium_test
    def test_view(self):
        self.workflow_index_open()
        self._workflow_import_from_url()
        self.workflow_index_click_option("View")
        title = self.wait_for_selector(".page-body h3")
        assert "TestWorkflow1" in title.text
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
            assert 'CoolNewName' == name, name

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

        self.workflow_index_click_tag_display()
        self.tagging_add(["cooltag"])

        @retry_assertion_during_transitions
        def check_tags():
            self.assertEqual(self.workflow_index_tags(), ["cooltag"])

        check_tags()
        self.screenshot("workflow_manage_tags")

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

    @retry_assertion_during_transitions
    def _assert_showing_n_workflows(self, n):
        self.assertEqual(len(self.workflow_index_table_elements()), n)

    @skip_if_github_down
    def _workflow_import_from_url(self):
        self.workflow_index_click_import()
        url = "https://raw.githubusercontent.com/galaxyproject/galaxy/release_19.09/test/base/data/test_workflow_1.ga"
        self.workflow_import_submit_url(url)
