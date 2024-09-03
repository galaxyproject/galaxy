from galaxy_test.base.workflow_fixtures import (
    WORKFLOW_WITH_BAD_COLUMN_PARAMETER,
    WORKFLOW_WITH_OLD_TOOL_VERSION,
)
from .framework import (
    managed_history,
    selenium_test,
    SeleniumTestCase,
)


class TestPages(SeleniumTestCase):
    ensure_registered = True

    @selenium_test
    @managed_history
    def test_simple_page_creation_edit_and_view(self):
        # Upload a file to test embedded object stuff
        test_path = self.get_filename("1.fasta")
        self.perform_upload(test_path)
        self.history_panel_wait_for_hid_ok(1)
        self.navigate_to_pages()
        self.screenshot("pages_grid")
        page_name = self.create_page_and_edit(screenshot_name="pages_create_form")
        self.screenshot("pages_editor_new")
        editor = self._page_editor
        editor.markdown_editor.wait_for_and_send_keys("moo\n\n\ncow\n\n")
        editor.embed_dataset.wait_for_and_click()
        self.screenshot("pages_editor_embed_dataset_dialog")
        editor.dataset_selector.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)
        editor.save.wait_for_and_click()
        self.screenshot("pages_editor_saved")
        self.page_open_and_screenshot(page_name, "page_view_with_embedded_dataset")

    @selenium_test
    @managed_history
    def test_workflow_problem_display(self):
        workflow_populator = self.workflow_populator
        problem_workflow_1_id = workflow_populator.upload_yaml_workflow(
            WORKFLOW_WITH_OLD_TOOL_VERSION, exact_tools=True
        )
        problem_workflow_2_id = workflow_populator.upload_yaml_workflow(
            WORKFLOW_WITH_BAD_COLUMN_PARAMETER, exact_tools=True
        )
        self.navigate_to_pages()
        page_name = self.create_page_and_edit()
        editor = self._page_editor
        editor.markdown_editor.wait_for_and_send_keys("moo\n\n\ncow\n\n")
        editor.embed_workflow_display.wait_for_and_click()
        self.screenshot("pages_editor_embed_workflow_dialog")
        editor.workflow_selection(id=problem_workflow_1_id).wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)
        editor.embed_workflow_display.wait_for_and_click()
        editor.workflow_selection(id=problem_workflow_2_id).wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)
        editor.save.wait_for_and_click()
        self.page_open_and_screenshot(page_name, "page_view_with_workflow_problems")

    @selenium_test
    @managed_history
    def test_history_links(self):
        new_history_name = self._get_random_name()
        self.history_panel_rename(new_history_name)
        self.current_history_publish()
        history_id = self.current_history_id()
        self.navigate_to_pages()
        page_name = self.create_page_and_edit()
        editor = self._page_editor
        editor.history_link.wait_for_and_click()
        editor.history_selection(id=history_id).wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)
        editor.save.wait_for_and_click()
        self.page_open_and_screenshot(page_name, "page_view_with_history_link")
        view = self.components.pages.view
        view.history_link(history_id=history_id).wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)
        self.navigate_to_histories_page()
        history_names = self.get_grid_entry_names("#histories-grid")
        assert f"Copy of '{new_history_name}'" in history_names

    @property
    def _page_editor(self):
        return self.components.pages.editor
