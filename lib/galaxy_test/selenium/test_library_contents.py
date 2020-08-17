import os

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
    def test_sub_folder(self):
        def change_description(description):
            self.components.libraries.folder.edit_folder_btn.wait_for_and_click()
            self.components.libraries.folder.input_folder_description.wait_for_visible().clear()
            self.components.libraries.folder.input_folder_description.wait_for_and_send_keys(description)
            self.components.libraries.folder.save_folder_btn.wait_for_and_click()

        sub_folder_name = self._get_random_name(prefix="new_sub_folder")
        description = self._get_random_name(prefix="new_sub_folder_description")
        long_description = self._get_random_name(prefix="new_sub_folder_description", len=45)

        # create mew folder
        self._navigate_to_new_library()
        self._assert_num_displayed_items_is(0)
        self.libraries_folder_create(sub_folder_name)
        self._assert_num_displayed_items_is(1)

        # check empty folder
        new_folder_link = self.wait_for_xpath_visible('//a[contains(text(), "%s")]' % sub_folder_name)
        new_folder_link.click()

        # assert that 'empty folder message' is present
        self.components.libraries.folder.empty_folder_message.wait_for_present()
        # go one folder up
        self.components.libraries.folder.btn_open_upper_folder.wait_for_and_click()
        # assert empty description
        self.components.libraries.folder.description_field.assert_absent_or_hidden()
        # change description
        change_description(description)
        assert description == self.components.libraries.folder.description_field.wait_for_text()
        change_description(long_description)

        # assert shrinked description

        shrinked_description = long_description[0:40]
        assert shrinked_description == self.components.libraries.folder.description_field_shrinked.wait_for_text()

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
        self.sleep_for(self.wait_types.UX_RENDER)
        self._select_history_option("dataset_add_bulk", "Unnamed history")
        self.sleep_for(self.wait_types.UX_RENDER)
        self.libraries_dataset_import_from_history_select(["1.txt"])
        # Add
        self.sleep_for(self.wait_types.UX_RENDER)
        self.screenshot("libraries_dataset_import")
        self.libraries_dataset_import_from_history_click_ok()
        self._assert_num_displayed_items_is(1)

    @selenium_test
    def download_dataset_from_library(self):
        self.test_import_dataset_from_history()

        self.components.libraries.folder.select_one.wait_for_and_click()
        self.components.libraries.folder.download_dropdown.wait_for_and_click()
        self.components.libraries.folder.download_zip.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)
        folder_files = os.listdir(self.get_download_path())

        expected_filename = "selected_dataset_files.zip"
        assert expected_filename in folder_files

    @selenium_test
    def test_delete_dataset(self):
        self.test_import_dataset_from_history()

        self.sleep_for(self.wait_types.UX_RENDER)
        # assert "you must select at least one" modal
        assert self.components.libraries.folder.toast_msg.is_displayed

        self.components.libraries.folder.delete_btn.wait_for_and_click()

        self.components.libraries.folder.select_one.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)

        self.components.libraries.folder.delete_btn.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)

        self._assert_num_displayed_items_is(0)

    # Fine test locally but the upload doesn't work in Docker compose. I'd think
    # Galaxy must be running so that test-data/1.txt would work but it just doesn't
    # for some reason. https://jenkins.galaxyproject.org/job/jmchilton-selenium/79/artifact/79-test-errors/test_import_dataset_from_path2017100413221507137721/
    @selenium_test
    def test_import_dataset_from_path(self):
        self._navigate_to_new_library()
        self._assert_num_displayed_items_is(0)
        self.sleep_for(self.wait_types.UX_RENDER)

        # Click the cancel button, make sure modal is hidden.
        self.libraries_dataset_import_from_path()
        self.wait_for_visible(self.navigation.libraries.folder.selectors.import_modal)
        self.wait_for_and_click(self.navigation.libraries.folder.selectors.import_datasets_cancel_button)
        self.wait_for_absent_or_hidden(self.navigation.libraries.folder.selectors.import_modal)

        # Try again... this time actually select some paths.
        self.libraries_dataset_import_from_path()
        textarea = self.wait_for_and_click(self.navigation.libraries.folder.selectors.import_from_path_textarea)
        textarea.send_keys("test-data/1.txt")
        self.sleep_for(self.wait_types.UX_RENDER)
        self.wait_for_and_click(self.navigation.libraries.folder.selectors.import_datasets_ok_button)
        # Let the progress bar disappear...
        self.wait_for_absent_or_hidden(self.navigation.libraries.folder.selectors.import_progress_bar)
        self._assert_num_displayed_items_is(1)

        self.click_label("1.txt")
        self.wait_for_visible(self.navigation.libraries.dataset.selectors.table)
        elements = self.find_elements(self.navigation.libraries.dataset.selectors.table_rows)
        table_as_dict = {}
        for element in elements:
            key = element.find_element_by_tag_name("th").text
            value = element.find_element_by_tag_name("td").text
            table_as_dict[key] = value

        assert table_as_dict["Name"] == "1.txt", table_as_dict
        assert table_as_dict["Genome build"] == "?", table_as_dict

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
