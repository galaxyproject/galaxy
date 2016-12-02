from .framework import (
    selenium_test,
    SeleniumTestCase
)


class WorkflowEditorTestCase(SeleniumTestCase):

    @selenium_test
    def test_build_workflow(self):
        self.navigate_to_workflow_landing(register=True)
        self.click_button_new_workflow()
        form_element = self.driver.find_element_by_css_selector("#center form")
        action = form_element.get_attribute("action")
        assert action.endswith("/workflow/create"), action

        name = self._get_random_name()
        annotation = self._get_random_name()
        self.fill(form_element, {
            'workflow_name': name,
            'workflow_annotation': annotation,
        })
        self.click_submit(form_element)

        element = self.wait_for_selector("#edit-attributes #workflow-name")
        assert name in element.text, element.text

    @selenium_test
    def test_import_from_url(self):
        self.navigate_to_workflow_landing(register=True)

        self.click_selector(self.test_data["selectors"]["workflows"]["import_button"])
        url = "https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test/api/test_workflow_1.ga"
        form_element = self.driver.find_element_by_css_selector("#center form")
        url_element = form_element.find_element_by_css_selector("input[type='text']")
        url_element.send_keys(url)
        self.click_submit(form_element)

        table_elements = self.driver.find_elements_by_css_selector(".manage-table tbody > tr")
        assert len(table_elements) == 2  # header plus first element

        new_workflow = table_elements[1].find_element_by_css_selector(".menubutton")
        assert 'TestWorkflow1 (imported from uploaded file)' in new_workflow.text, new_workflow.text

    def navigate_to_workflow_landing(self, register=False):
        if register:
            self.register()
        self.home()
        self.click_masthead_workflow()
