from .framework import (
    selenium_test,
    SeleniumTestCase,
)


class TestPageSharing(SeleniumTestCase):
    ensure_registered = True

    @selenium_test
    def test_publish_page(self):
        page_id = self.dataset_populator.new_page()["id"]
        self.go_to_page_sharing(page_id)
        self.make_accessible_and_publishable()
        published_href = self.components.histories.sharing.published_items_link.wait_for_visible().get_attribute("href")
        assert published_href.endswith("/pages/list_published"), published_href
        sharing_status = self.dataset_populator.wait_for_published("pages", page_id)
        assert sharing_status["importable"] is True, sharing_status
