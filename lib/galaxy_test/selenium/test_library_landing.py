from .framework import (
    retry_assertion_during_transitions,
    selenium_test,
    SeleniumTestCase,
)


class LibraryLandingTestCase(SeleniumTestCase):

    requires_admin = True

    def setup_with_driver(self):
        super().setup_with_driver()
        self.admin_login()
        self.libraries_open()

    @selenium_test
    def test_create_new_close(self):
        num_displayed_libraries = self._num_displayed_libraries()
        self.components.libraries.create_new_library_btn.wait_for_and_click()
        self.wait_for_selector_visible(".new-row")
        self.screenshot("libraries_new")
        self.components.libraries.create_new_library_btn.wait_for_and_click()
        self.wait_for_overlays_cleared()
        assert self._num_displayed_libraries() == num_displayed_libraries

    @selenium_test
    def test_create_new(self):
        name = self._get_random_name(prefix="testcreatenew")
        self.libraries_index_create(name)

        # Must be showing at least one library now.
        self._assert_at_least_one_library_displayed()

        self._search_for_only_with_name(name)

    @selenium_test
    def test_rename(self):
        name = self._get_random_name(prefix="testprerename")
        self.libraries_index_create(name)
        self._search_for_only_with_name(name)

        edit_button = self.wait_for_selector_clickable(".edit_library_btn")
        edit_button.click()

        new_name = self._get_random_name(prefix="testpostrename")
        name_box = self.wait_for_selector_clickable(".input_library_name")
        name_box.send_keys(new_name)

        self.screenshot("libraries_rename")
        save_button = self.wait_for_selector_clickable(".save_library_btn")
        save_button.click()

        self._search_for_only_with_name(new_name)

    @selenium_test
    def test_sorting(self):
        # Throw in another library to ensure filtering is working...
        other = self._get_random_name(prefix="notthesame")
        self.libraries_index_create(other)
        self.wait_for_overlays_cleared()

        namebase = self._get_random_name(prefix="testsort")
        self.libraries_index_create(f"{namebase} b")
        self.wait_for_overlays_cleared()
        self.libraries_index_create(f"{namebase} a")
        self.wait_for_overlays_cleared()
        self.libraries_index_create(f"{namebase} c")

        self.screenshot("libraries_index")

        self.libraries_index_search_for(namebase)

        self._assert_num_displayed_libraries_is(3)
        self.screenshot("libraries_index_search")
        # sort ascending
        self.libraries_index_sort_click()
        self._assert_names_are([f"{namebase} a", f"{namebase} b", f"{namebase} c"])
        # sort descending
        self.libraries_index_sort_click()
        self._assert_names_are([f"{namebase} c", f"{namebase} b", f"{namebase} a"])

    def _search_for_only_with_name(self, name):
        self.libraries_index_search_for(name)
        self._assert_num_displayed_libraries_is(1)

    @retry_assertion_during_transitions
    def _assert_names_are(self, expected_names):
        names = [e.find_element_by_css_selector("td a").text for e in self.libraries_index_table_elements()]
        self.assertEqual(names, expected_names)

    @retry_assertion_during_transitions
    def _assert_at_least_one_library_displayed(self):
        assert self._num_displayed_libraries() > 0

    @retry_assertion_during_transitions
    def _assert_num_displayed_libraries_is(self, n):
        self.assertEqual(n, self._num_displayed_libraries())

    def _num_displayed_libraries(self):
        return len(self.libraries_index_table_elements())
