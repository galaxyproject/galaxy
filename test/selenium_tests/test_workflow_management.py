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

        new_workflow = table_elements[0].find_element_by_css_selector(".menubutton")
        assert 'TestWorkflow1 (imported from uploaded file)' in new_workflow.text, new_workflow.text

    @selenium_test
    def test_view(self):
        self.workflow_index_open()
        self._workflow_import_from_url()
        self.workflow_index_click_option("View")
        title = self.wait_for_selector(".page-body h3")
        assert "TestWorkflow1" in title.text

        # TODO: Test display of steps...

    @selenium_test
    def test_rename(self):
        self.workflow_index_open()
        self._workflow_import_from_url()
        self.workflow_index_rename("CoolNewName")

        @retry_assertion_during_transitions
        def check_name():
            row_element = self.workflow_index_table_row()
            renamed_workflow_button = row_element.find_element_by_css_selector(".menubutton")
            assert 'CoolNewName' in renamed_workflow_button.text, renamed_workflow_button.text

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

    @selenium_test
    def test_index_search(self):
        self.workflow_index_open()
        self._workflow_import_from_url()
        self.workflow_index_rename("searchforthis")
        self._assert_showing_n_workflows(1)

        search_box = self.workflow_index_click_search()
        search_box.send_keys("doesnotmatch")
        self._assert_showing_n_workflows(0)

        # Prevent stale element textbox by re-fetching, seems to be
        # needed but I don't understand why exactly. -John
        search_box = self.workflow_index_click_search()
        search_box.clear()
        self.send_enter(search_box)
        self._assert_showing_n_workflows(1)

        search_box = self.workflow_index_click_search()
        search_box.send_keys("searchforthis")
        self.send_enter(search_box)
        self._assert_showing_n_workflows(1)

    @selenium_test
    def test_publishing_display(self):
        self.workflow_index_open()
        self._workflow_import_from_url()
        self.workflow_index_rename("managementesttopublish")

        row_element = self.workflow_index_table_row()
        columns = row_element.find_elements_by_css_selector("td")
        assert columns[4].text == "No"

        self.workflow_index_click_option("Share")
        self.workflow_sharing_click_publish()

        self.workflow_index_open()
        row_element = self.workflow_index_table_row()
        columns = row_element.find_elements_by_css_selector("td")
        assert columns[4].text == "Yes"

    @retry_assertion_during_transitions
    def _assert_showing_n_workflows(self, n):
        self.assertEqual(len(self.workflow_index_table_elements()), n)

    def _workflow_import_from_url(self):
        self.workflow_index_click_import()
        url = "https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test/base/data/test_workflow_1.ga"
        self.workflow_import_submit_url(url)
