from .framework import (
    managed_history,
    playwright_only,
    selenium_test,
    SeleniumTestCase,
)
from .upload_activity_helpers import UsesUploadActivity


class TestAnotherGalaxyPicker(SeleniumTestCase, UsesUploadActivity):
    """Import from this Galaxy into itself under its other host name, so the popup is really cross-origin."""

    ensure_registered = True

    @selenium_test
    @managed_history
    @playwright_only("The popup is closed by the page, which the Selenium visit_new_window cannot survive")
    def test_choose_dataset_in_popup_and_import_it(self):
        self.upload_context("paste-content").stage_paste_content("picked content", {"name": "picked"}).start()
        self.history_panel_wait_for_hid_ok(1)
        dataset = self.dataset_populator.get_history_dataset_details(self.current_history_id(), hid=1)
        source_url = self.target_url_from_selenium
        target_url = source_url.replace("127.0.0.1", "localhost")
        assert target_url != source_url

        # The target gets its own session and origin; links back to 127.0.0.1 pass fetch_url_allowlist.
        email = self.get_user_email()
        self.target_url_from_selenium = target_url
        self.home()
        self.submit_login(email)

        upload = self.components.upload_activity
        upload.activity.wait_for_and_click()
        upload.method_card(method_id="galaxy-link").wait_for_and_click()
        upload.galaxy_picker_server.wait_for_visible()
        upload.galaxy_picker_server.select_by_value("other")
        upload.galaxy_picker_url.wait_for_and_send_keys(source_url)
        upload.galaxy_picker_open.wait_for_and_click()

        picker = self.components.another_galaxy_picker
        with self.visit_new_window():
            picker.select(key=f"dataset:{dataset['id']}").wait_for_and_click()
            assert "usually after 24 hours" in picker.consent.wait_for_visible().text
            picker.send.wait_for_and_click()
            # The opener closes the popup once it has the links.
            self.page.wait_for_event("close", timeout=self.wait_length(self.wait_types.JOB_COMPLETION) * 1000)

        item = upload.galaxy_picker_import_item
        self._wait_on(
            lambda: "Imported" in item.wait_for_visible().text or None,
            "the import to finish",
            wait_type=self.wait_types.JOB_COMPLETION,
        )
        # API calls here carry the session of either host name, so find the copy by what it is, not the current history.
        matches = self.dataset_populator._get("datasets", {"q": "name-eq", "qv": "picked"}).json()
        copies = [match for match in matches if match["id"] != dataset["id"]]
        assert len(copies) == 1
        history_id, dataset_id = copies[0]["history_id"], copies[0]["id"]
        content = self.dataset_populator.get_history_dataset_content(history_id, dataset_id=dataset_id)
        assert content == "picked content\n"
