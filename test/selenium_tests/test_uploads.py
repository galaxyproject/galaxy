from .framework import SeleniumTestCase
from .framework import selenium_test


class UploadsTestCase(SeleniumTestCase):

    @selenium_test
    def test_simple_upload(self):
        self.home()
        self.register()
        self.perform_upload(self.get_filename("1.sam"))

        histories = self.api_get("histories")
        current_id = histories[0]["id"]
        self.history_panel_wait_for_hid_ok(1)

        history_contents = self.api_get("histories/%s/contents" % current_id)
        history_count = len(history_contents)
        assert history_count == 1, "Incorrect number of items in history - expected 1, found %d" % history_count

        hda = history_contents[0]
        assert hda["name"] == '1.sam'
