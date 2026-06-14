"""Integration test for direct-download redirects (presigned URLs) from a remote object store.

Datasets stored in a backing object store with ``enable_direct_download`` set should be served via a
302 redirect to a URL the client fetches directly from the store, instead of being pulled through
Galaxy's cache. Uses a boto3 object store backed by a disposable minio container.
"""

import os
import string

import requests

from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util
from galaxy_test.driver.integration_util import docker_rm
from ._base import (
    BaseObjectStoreIntegrationTestCase,
    files_count,
    OBJECT_STORE_ACCESS_KEY,
    OBJECT_STORE_HOST,
    OBJECT_STORE_PORT,
    OBJECT_STORE_SECRET_KEY,
    start_minio,
)

BOTO3_DIRECT_DOWNLOAD_CONFIG = string.Template("""
<object_store type="boto3" enable_direct_download="true">
    <auth access_key="${access_key}" secret_key="${secret_key}" />
    <bucket name="galaxy" />
    <connection endpoint_url="http://${host}:${port}" />
    <cache path="${temp_directory}/object_store_cache" size="1000" />
    <extra_dir type="job_work" path="${temp_directory}/job_working_directory_boto3"/>
    <extra_dir type="temp" path="${temp_directory}/tmp_boto3"/>
</object_store>
""")


@integration_util.skip_unless_docker()
class TestDirectDownloadRedirectIntegration(BaseObjectStoreIntegrationTestCase):
    container_name: str
    object_store_cache_path: str

    @classmethod
    def setUpClass(cls):
        cls.container_name = f"{cls.__name__}_container"
        start_minio(cls.container_name)
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        docker_rm(cls.container_name)
        super().tearDownClass()

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        temp_directory = cls._test_driver.mkdtemp()
        cls.object_stores_parent = temp_directory
        cls.object_store_cache_path = os.path.join(temp_directory, "object_store_cache")
        config_path = os.path.join(temp_directory, "object_store_conf.xml")
        config["object_store_store_by"] = "uuid"
        with open(config_path, "w") as f:
            f.write(
                BOTO3_DIRECT_DOWNLOAD_CONFIG.safe_substitute(
                    {
                        "temp_directory": temp_directory,
                        "host": OBJECT_STORE_HOST,
                        "port": OBJECT_STORE_PORT,
                        "access_key": OBJECT_STORE_ACCESS_KEY,
                        "secret_key": OBJECT_STORE_SECRET_KEY,
                    }
                )
            )
        config["object_store_config_file"] = config_path

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def _display_url(self, hda_id, **params):
        return self._api_url(f"datasets/{hda_id}/display", params=params, use_key=True)

    def test_download_redirects_to_presigned_url(self):
        history_id = self.dataset_populator.new_history()
        hda = self.dataset_populator.new_dataset(history_id, content="123", wait=True)

        # Clear the cache so we can prove the download is served without pulling the object back in.
        self._reset_cache()
        assert files_count(self.object_store_cache_path) == 0

        url = self._display_url(hda["id"], to_ext="txt")
        response = requests.get(url, allow_redirects=False)
        assert response.status_code == 302
        location = response.headers["Location"]
        assert OBJECT_STORE_HOST in location
        # The presigned URL carries the download filename so the client gets a sensible name.
        assert "response-content-disposition" in location.lower()

        # The redirect target is fetchable directly from the object store and holds the data.
        direct_response = requests.get(location)
        direct_response.raise_for_status()
        assert direct_response.content == b"123\n"

        # Galaxy served the download without pulling the object into its cache.
        assert files_count(self.object_store_cache_path) == 0

    def test_raw_download_redirects(self):
        history_id = self.dataset_populator.new_history()
        hda = self.dataset_populator.new_dataset(history_id, content="raw-bytes", wait=True)

        url = self._display_url(hda["id"], raw="True")
        response = requests.get(url, allow_redirects=False)
        assert response.status_code == 302
        assert OBJECT_STORE_HOST in response.headers["Location"]

    def test_preview_is_not_redirected(self):
        history_id = self.dataset_populator.new_history()
        hda = self.dataset_populator.new_dataset(history_id, content="hello", wait=True)

        # A preview (not a download) is processed by the datatype and streamed through Galaxy.
        url = self._display_url(hda["id"], preview="True")
        response = requests.get(url, allow_redirects=False)
        assert response.status_code == 200
        assert "hello" in response.text

    def _reset_cache(self):
        for root, _, files in os.walk(self.object_store_cache_path):
            for file_ in files:
                os.remove(os.path.join(root, file_))
