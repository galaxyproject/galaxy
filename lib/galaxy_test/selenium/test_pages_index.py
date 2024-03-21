from .framework import (
    retry_assertion_during_transitions,
    selenium_test,
    SeleniumTestCase,
)


class TestPagesIndex(SeleniumTestCase):
    ensure_registered = True

    @selenium_test
    def test_page_deletion(self):
        page_response = self.new_page()
        page_title = page_response["title"]
        self.navigate_to_pages()
        self._assert_showing_n_pages(1)
        self.select_grid_operation(page_title, "Delete")
        alert = self.driver.switch_to.alert
        alert.accept()
        self._assert_showing_n_pages(0)

    def new_page(self):
        slug = self._get_random_name()
        response = self.dataset_populator.new_page(slug=slug)
        return response

    @retry_assertion_during_transitions
    def _assert_showing_n_pages(self, n):
        if (actual_count := len(self.get_grid_entry_names("#pages-grid"))) != n:
            message = f"Expected {n} pages to be displayed, based on DOM found {actual_count} page index rows."
            raise AssertionError(message)
