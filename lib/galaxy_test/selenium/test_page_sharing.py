from .framework import (
    selenium_test,
    SeleniumTestCase,
)


class TestPageSharing(SeleniumTestCase):
    ensure_registered = True

    @selenium_test
    def test_publish_page(self):
        page_id = self.dataset_populator.new_page(slug="page-sharing")["id"]
        self.go_to_page_sharing(page_id)
        self.make_accessible_and_publishable()
        self.wait_for_selector(".make-publishable a[href$='/pages/list_published']")
        self._wait_on_custom(
            lambda driver=None: self.api_get(f"pages/{page_id}/sharing")["published"],
            "page to be published",
        )
        sharing = self.api_get(f"pages/{page_id}/sharing")
        assert sharing["importable"] is True, sharing
        assert sharing["published"] is True, sharing
