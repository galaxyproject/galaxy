import os

from galaxy_test.base.populators import (
    DatasetPopulator,
    uses_test_history,
)
from galaxy_test.driver.integration_util import IntegrationTestCase


class NginxAccelHeaderIntegrationTestCase(IntegrationTestCase):
    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["nginx_x_accel_redirect_base"] = "/redirect"

    @uses_test_history()
    def test_dataset_download(self, history_id):
        hda = self.dataset_populator.new_dataset(history_id=history_id, wait=True)
        head_response = self._head(f"histories/{history_id}/contents/{hda['id']}/display", {"raw": "True"})
        self._assert_status_code_is(head_response, 200)
        assert head_response.headers["content-length"] == "12"
        display_response = self._get(f"histories/{history_id}/contents/{hda['id']}/display", {"raw": "True"})
        self._assert_status_code_is(display_response, 200)
        assert display_response.headers["content-length"] == "0"
        assert display_response.headers["x-accel-redirect"].startswith("/redirect")


class ApacheSendFileHeaderIntegrationTestCase(IntegrationTestCase):
    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["apache_xsendfile"] = True

    @uses_test_history()
    def test_dataset_download(self, history_id):
        hda = self.dataset_populator.new_dataset(history_id=history_id, wait=True)
        head_response = self._head(f"histories/{history_id}/contents/{hda['id']}/display", {"raw": "True"})
        self._assert_status_code_is(head_response, 200)
        assert head_response.headers["content-length"] == "12"
        display_response = self._get(f"histories/{history_id}/contents/{hda['id']}/display", {"raw": "True"})
        self._assert_status_code_is(display_response, 200)
        assert display_response.headers["content-length"] == "0"
        assert "x-sendfile" in display_response.headers
        assert os.path.exists(display_response.headers["x-sendfile"])
