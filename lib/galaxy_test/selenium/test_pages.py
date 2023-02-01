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
        name = self.create_page_and_edit(screenshot_name="pages_create_form")
        self.screenshot("pages_editor_new")
        self.components.pages.editor.markdown_editor.wait_for_and_send_keys("moo\n\n\ncow\n\n")
        self.components.pages.editor.embed_dataset.wait_for_and_click()
        self.screenshot("pages_editor_embed_dataset_dialog")
        self.components.pages.editor.dataset_selector.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)
        self.components.pages.editor.save.wait_for_and_click()
        self.screenshot("pages_editor_saved")
        self.home()
        self.navigate_to_pages()
        self.click_grid_popup_option(name, "View")
        self.screenshot("pages_view_simple")
