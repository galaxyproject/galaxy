from .framework import (
    selenium_test,
    SeleniumTestCase
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
        self.workflow_index_click_option("Rename")
        rename_form_element = self.wait_for_selector("form")
        self.fill(rename_form_element, {
            "new_name": "CoolNewName"
        })
        self.click_submit(rename_form_element)

        table_elements = self.workflow_index_table_elements()
        renamed_workflow_button = table_elements[0].find_element_by_css_selector(".menubutton")
        assert 'CoolNewName' in renamed_workflow_button.text, renamed_workflow_button.text

    def _workflow_import_from_url(self):
        self.click_selector(self.test_data["selectors"]["workflows"]["import_button"])
        url = "https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test/base/data/test_workflow_1.ga"
        form_element = self.driver.find_element_by_css_selector("#center form")
        url_element = form_element.find_element_by_css_selector("input[type='text']")
        url_element.send_keys(url)
        self.click_submit(form_element)
