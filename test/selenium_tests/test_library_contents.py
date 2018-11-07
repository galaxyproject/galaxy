from selenium.webdriver.support.ui import Select

from .framework import (
    retry_assertion_during_transitions,
    retry_during_transitions,
    selenium_test,
    SeleniumTestCase,
)


class LibraryContentsTestCase(SeleniumTestCase):

    requires_admin = True

    @selenium_test
    def test_create_folder(self):
        self._navigate_to_new_library()
        self._assert_num_displayed_items_is(0)
        self.libraries_folder_create("folder1")
        self._assert_num_displayed_items_is(1)

    @selenium_test
    def test_import_dataset_from_history(self):
        self.admin_login()
        self.perform_upload(self.get_filename("1.txt"))
        self.wait_for_history()
        self._navigate_to_new_library(login=False)
        self._assert_num_displayed_items_is(0)
        self.sleep_for(self.wait_types.UX_RENDER)
        self.libraries_dataset_import_from_history()
        # Click the cancel button, make sure modal is hidden.
        self.wait_for_visible(self.navigation.libraries.folder.selectors.import_modal)
        self.wait_for_and_click(self.navigation.libraries.folder.selectors.import_datasets_cancel_button)
        self.wait_for_absent_or_hidden(self.navigation.libraries.folder.selectors.import_modal)

        self.libraries_dataset_import_from_history()
        # Need to select the right item on the dropdown
        self._select_history_option("dataset_add_bulk", "Unnamed history")
        self.sleep_for(self.wait_types.UX_RENDER)
        self.libraries_dataset_import_from_history_select(["1.txt"])
        # Add
        self.sleep_for(self.wait_types.UX_RENDER)
        self.screenshot("libraries_dataset_import")
        self.libraries_dataset_import_from_history_click_ok()
        self._assert_num_displayed_items_is(1)

    # Fine test locally but the upload doesn't work in Docker compose. I'd think
    # Galaxy must be running so that test-data/1.txt would work but it just doesn't
    # for some reason. https://jenkins.galaxyproject.org/job/jmchilton-selenium/79/artifact/79-test-errors/test_import_dataset_from_path2017100413221507137721/
    # @selenium_test
    # def test_import_dataset_from_path(self):
    #     self._navigate_to_new_library()
    #     self._assert_num_displayed_items_is(0)
    #     self.sleep_for(self.wait_types.UX_RENDER)

    #     # Click the cancel button, make sure modal is hidden.
    #     self.libraries_dataset_import_from_path()
    #     self.wait_for_visible(self.navigation.libraries.folder.selectors.import_modal)
    #     self.wait_for_and_click(self.navigation.libraries.folder.selectors.import_datasets_cancel_button)
    #     self.wait_for_absent_or_hidden(self.navigation.libraries.folder.selectors.import_modal)

    #     # Try again... this time actually select some paths.
    #     self.libraries_dataset_import_from_path()
    #     textarea = self.wait_for_and_click(self.navigation.libraries.folder.selectors.import_from_path_textarea)
    #     textarea.send_keys("test-data/1.txt")
    #     self.sleep_for(self.wait_types.UX_RENDER)
    #     self.wait_for_and_click(self.navigation.libraries.folder.selectors.import_datasets_ok_button)
    #     # Let the progress bar disappear...
    #     self.wait_for_absent_or_hidden(self.navigation.libraries.folder.selectors.import_progress_bar)
    #     self._assert_num_displayed_items_is(1)

    #     self.click_label("1.txt")
    #     self.wait_for_visible(self.navigation.libraries.dataset.selectors.table)
    #     elements = self.find_elements(self.navigation.libraries.dataset.selectors.table_rows)
    #     table_as_dict = {}
    #     for element in elements:
    #         key = element.find_element_by_tag_name("th").text
    #         value = element.find_element_by_tag_name("td").text
    #         table_as_dict[key] = value

    #     assert table_as_dict["Name"] == "1.txt", table_as_dict
    #     assert table_as_dict["Genome build"] == "?", table_as_dict

    @selenium_test
    def test_show_details(self):
        self._navigate_to_new_library()
        self.sleep_for(self.wait_types.UX_RENDER)
        self.wait_for_selector_clickable(".toolbtn-show-locinfo").click()
        self.sleep_for(self.wait_types.UX_RENDER)
        self.wait_for_selector_clickable(".ui-modal #button-0").click()
        self.wait_for_overlays_cleared()
        self.screenshot("libraries_show_details")

    @retry_assertion_during_transitions
    def _assert_num_displayed_items_is(self, n):
        self.assertEqual(n, self._num_displayed_items())

    def _num_displayed_items(self):
        return len(self.libraries_table_elements())

    def _navigate_to_new_library(self, login=True):
        if login:
            self.admin_login()
        self.libraries_open()
        self.name = self._get_random_name(prefix="testcontents")
        self.libraries_index_create(self.name)
        self.libraries_open_with_name(self.name)

    @retry_during_transitions
    def _select_history_option(self, select_id, label_text):
        select = Select(self.driver.find_element_by_id(select_id))
        select.select_by_visible_text(label_text)
