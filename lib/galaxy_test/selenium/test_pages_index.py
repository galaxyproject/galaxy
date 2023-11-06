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
        page_id = page_response["id"]
        self.navigate_to_pages()
        self._assert_showing_n_pages(1)
        self.components.pages.dropdown(id=page_id).wait_for_visible()
        self.page_index_click_option("Delete", page_id)
        self.sleep_for(self.wait_types.UX_RENDER)
        self.components.pages.delete_modal_confirm(id=page_id).wait_for_and_click()
        self.components.pages.dropdown(id=page_id).wait_for_absent_or_hidden()
        self._assert_showing_n_pages(0)

    def new_page(self):
        slug = self._get_random_name()
        response = self.dataset_populator.new_page(slug=slug)
        return response

    @retry_assertion_during_transitions
    def _assert_showing_n_pages(self, n):
        actual_count = len(self.pages_index_table_elements())
        if actual_count != n:
            message = f"Expected {n} pages to be displayed, based on DOM found {actual_count} page index rows."
            raise AssertionError(message)
