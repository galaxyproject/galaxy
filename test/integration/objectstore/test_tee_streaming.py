"""Integration test for tee-streaming dataset downloads from a remote object store.

An uncached whole-file download is proxied straight from the backing store to the client while the
bytes are written into Galaxy's cache on the way past, so the client gets its first byte immediately
instead of waiting for the whole object to be pulled in -- and objects too big for the cache can be
downloaded at all. Requests that need random access (Range, HEAD) still get a cached file. Runs
against a boto3 object store and a cloudbridge (cloud) object store, each backed by a disposable
minio container.
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

BOTO3_TEE_STREAMING_CONFIG = string.Template("""
<object_store type="boto3">
    <auth access_key="${access_key}" secret_key="${secret_key}" />
    <bucket name="galaxy" />
    <connection endpoint_url="http://${host}:${port}" />
    <cache path="${temp_directory}/object_store_cache" size="1000" />
    <extra_dir type="job_work" path="${temp_directory}/job_working_directory_boto3"/>
    <extra_dir type="temp" path="${temp_directory}/tmp_boto3"/>
</object_store>
""")

CLOUD_TEE_STREAMING_CONFIG = string.Template("""
<object_store type="cloud" provider="aws">
    <auth access_key="${access_key}" secret_key="${secret_key}" />
    <bucket name="galaxy" use_reduced_redundancy="False" />
    <connection endpoint_url="http://${host}:${port}" />
    <cache path="${temp_directory}/object_store_cache" size="1000" />
    <extra_dir type="job_work" path="${temp_directory}/job_working_directory_cloud"/>
    <extra_dir type="temp" path="${temp_directory}/tmp_cloud"/>
</object_store>
""")

# ~107 bytes of cache: smaller than the datasets this test downloads through it.
BOTO3_TINY_CACHE_CONFIG = string.Template("""
<object_store type="boto3">
    <auth access_key="${access_key}" secret_key="${secret_key}" />
    <bucket name="galaxy" />
    <connection endpoint_url="http://${host}:${port}" />
    <cache path="${temp_directory}/object_store_cache" size="0.0000001" />
    <extra_dir type="job_work" path="${temp_directory}/job_working_directory_tiny"/>
    <extra_dir type="temp" path="${temp_directory}/tmp_tiny"/>
</object_store>
""")


class TeeStreamingIntegrationTestCase(BaseObjectStoreIntegrationTestCase):
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
                cls.object_store_config.safe_substitute(
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

    def _reset_cache(self):
        for root, _, files in os.walk(self.object_store_cache_path):
            for file_ in files:
                os.remove(os.path.join(root, file_))


@integration_util.skip_unless_docker()
class TestTeeStreamingIntegration(TeeStreamingIntegrationTestCase):
    object_store_config = BOTO3_TEE_STREAMING_CONFIG

    def test_uncached_download_streams_and_warms_cache(self):
        history_id = self.dataset_populator.new_history()
        hda = self.dataset_populator.new_dataset(history_id, content="tee-me", wait=True)

        self._reset_cache()
        assert files_count(self.object_store_cache_path) == 0

        response = requests.get(self._display_url(hda["id"], to_ext="txt"))

        assert response.status_code == 200
        assert response.content == b"tee-me\n"
        # Streamed from the store, not served off disk: a one-shot stream cannot answer ranges.
        assert "accept-ranges" not in response.headers
        # The size is known from the store's metadata, so the client still gets a progress bar.
        assert response.headers["Content-Length"] == str(len(b"tee-me\n"))
        # The bytes were written into the cache on their way to the client.
        assert files_count(self.object_store_cache_path) == 1

    def test_cached_download_is_served_from_the_cache(self):
        history_id = self.dataset_populator.new_history()
        hda = self.dataset_populator.new_dataset(history_id, content="cache-me", wait=True)

        self._reset_cache()
        url = self._display_url(hda["id"], to_ext="txt")
        first = requests.get(url)
        assert first.status_code == 200
        assert "accept-ranges" not in first.headers

        second = requests.get(url)

        assert second.status_code == 200
        assert second.content == b"cache-me\n"
        # Now served from the warmed cache file, which does support ranges.
        assert second.headers["accept-ranges"] == "bytes"

    def test_range_request_is_served_from_the_cache(self):
        history_id = self.dataset_populator.new_history()
        hda = self.dataset_populator.new_dataset(history_id, content="0123456789", wait=True)

        self._reset_cache()
        response = requests.get(self._display_url(hda["id"], to_ext="txt"), headers={"Range": "bytes=0-3"})

        # A range request needs random access, so it falls back to pulling the object into the cache.
        assert response.status_code == 206
        assert response.content == b"0123"
        assert files_count(self.object_store_cache_path) == 1

    def test_head_request_does_not_stream_the_object(self):
        history_id = self.dataset_populator.new_history()
        hda = self.dataset_populator.new_dataset(history_id, content="head-me", wait=True)

        self._reset_cache()
        response = requests.head(self._display_url(hda["id"], to_ext="txt"))

        # A HEAD wants headers only -- consuming a stream to throw the bytes away would be waste.
        assert response.status_code == 200
        assert response.headers["accept-ranges"] == "bytes"

    def test_preview_is_not_streamed(self):
        history_id = self.dataset_populator.new_history()
        hda = self.dataset_populator.new_dataset(history_id, content="preview-me", wait=True)

        self._reset_cache()
        response = requests.get(self._display_url(hda["id"], preview="True"))

        # A preview is processed by the datatype, so it needs the object on disk.
        assert response.status_code == 200
        assert "preview-me" in response.text


@integration_util.skip_unless_docker()
class TestCloudTeeStreamingIntegration(TestTeeStreamingIntegration):
    object_store_config = CLOUD_TEE_STREAMING_CONFIG


@integration_util.skip_unless_docker()
class TestTeeStreamingBiggerThanCacheIntegration(TeeStreamingIntegrationTestCase):
    object_store_config = BOTO3_TINY_CACHE_CONFIG

    def test_download_bigger_than_cache_succeeds_without_writing_the_cache(self):
        history_id = self.dataset_populator.new_history()
        content = "x" * 500
        hda = self.dataset_populator.new_dataset(history_id, content=content, wait=True)

        self._reset_cache()
        assert files_count(self.object_store_cache_path) == 0

        response = requests.get(self._display_url(hda["id"], to_ext="txt"))

        # Too big for the cache to hold: before tee-streaming this download failed outright.
        assert response.status_code == 200
        assert response.content == f"{content}\n".encode()
        # Streamed straight through -- nothing was written to the cache it does not fit in.
        assert files_count(self.object_store_cache_path) == 0
