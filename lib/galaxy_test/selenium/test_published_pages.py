from .framework import (
    selenium_test,
    SharedStateSeleniumTestCase,
)


class TestPublishedPagesGrid(SharedStateSeleniumTestCase):
    @selenium_test
    def test_index(self):
        self.navigate_to_pages()
        assert len(self.get_grid_entry_names("#pages-published-grid")) == 2

    def setup_shared_state(self):
        self.user1_email = self._get_random_email("test1")
        self.user2_email = self._get_random_email("test2")
        self.register(self.user1_email)
        page_1 = self.new_public_page()
        self.page_id_1 = page_1["id"]
        self.slug_1 = page_1["slug"]
        self.logout_if_needed()

        self.register(self.user2_email)
        page_2 = self.new_public_page()
        self.page_id_2 = page_2["id"]
        self.slug_2 = page_2["slug"]

    def new_public_page(self):
        slug = self._get_random_name()
        response = self.dataset_populator.new_page(slug=slug)
        self.dataset_populator.make_page_public(response["id"])
        return response
