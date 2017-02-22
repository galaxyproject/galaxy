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

        history_contents = self.api_get("histories/%s/contents" % current_id)
        assert len(history_contents) == 1

        hda = history_contents[0]
        assert hda["name"] == '1.sam'
