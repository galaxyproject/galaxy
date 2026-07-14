"""Integration tests for structured datasets (currently only HDF5 supported).

This file checks the ability to access datasets using the get_structured_content
API and services.
"""

import io
import os
import tempfile
from urllib.parse import urlencode

import h5py
import numpy as np

from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util

SCRIPT_DIR = os.path.normpath(os.path.dirname(__file__))
TEST_DATA_DIRECTORY = os.path.join(SCRIPT_DIR, os.pardir, os.pardir, "test-data")

BIG_ARRAY = np.arange(2_000_000, dtype=np.uint8) % 251


def _build_structured_fixture(path):
    with h5py.File(path, "w", libver="latest") as f:
        f.create_dataset("big", data=BIG_ARRAY)
        f["big"].attrs["big_attr"] = np.zeros(2_000_000, dtype=np.uint8)
        f.create_dataset("small_vlen", data=["a", "bb", "ccc"])
        f.create_dataset("big_vlen", data=[str(i) for i in range(2000)])


class TestStructuredDataset(integration_util.IntegrationTestCase):
    require_admin_user = True
    dataset_populator: DatasetPopulator
    test_history_id: str
    _fixture_path = None
    _upload_cache: dict = {}

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.test_history_id = self.dataset_populator.new_history()

    @classmethod
    def _structured_fixture_path(cls):
        if cls._fixture_path is None:
            path = os.path.join(tempfile.mkdtemp(), "structured.h5")
            _build_structured_fixture(path)
            cls._fixture_path = path
        return cls._fixture_path

    def _dataset_id(self, source_uri, file_type="h5"):
        if source_uri not in type(self)._upload_cache:
            dataset = self.dataset_populator.new_dataset(
                self.test_history_id, source_uri, file_type=file_type, wait=True
            )
            type(self)._upload_cache[source_uri] = dataset["dataset_id"]
        return type(self)._upload_cache[source_uri]

    def _chopper_dataset_id(self):
        return self._dataset_id(f"file://{TEST_DATA_DIRECTORY}/chopper.h5")

    def _big_dataset_id(self):
        return self._dataset_id(f"file://{self._structured_fixture_path()}")

    def _content(self, dataset_id, content_type, **params):
        query = f"?{urlencode(params)}" if params else ""
        return self._get(f"datasets/{dataset_id}/content/{content_type}{query}")

    def test_fail_on_nonbinary(self):
        dataset_id = self._dataset_id(f"file://{TEST_DATA_DIRECTORY}/random-file", file_type="txt")
        response = self._content(dataset_id, "meta")
        self._assert_status_code_is(response, 500)

    def test_api_meta(self):
        response = self._content(self._chopper_dataset_id(), "meta")
        self._assert_status_code_is(response, 200)
        self._assert_has_keys(response.json(), "attributes", "name", "kind")

    def test_api_attr(self):
        response = self._content(self._chopper_dataset_id(), "attr")
        self._assert_status_code_is(response, 200)
        self._assert_has_keys(response.json(), "HDF5_Version", "NeXus_version", "default", "file_name", "file_time")

    def test_api_stats(self):
        response = self._content(self._chopper_dataset_id(), "stats", path="/entry/data/data")
        self._assert_status_code_is(response, 200)
        self._assert_has_keys(response.json(), "strict_positive_min", "positive_min", "min", "max", "mean", "std")

    def test_api_data(self):
        response = self._content(self._chopper_dataset_id(), "data", path="/entry/data/data")
        self._assert_status_code_is(response, 200)
        assert len(response.json()) == 148

    def test_data_json_over_limit_rejected(self):
        response = self._content(self._big_dataset_id(), "data", path="/big")
        self._assert_status_code_is(response, 400)
        assert "selection" in response.text.lower()

    def test_data_json_with_selection(self):
        response = self._content(self._big_dataset_id(), "data", path="/big", selection="0:100")
        self._assert_status_code_is(response, 200)
        assert response.json() == BIG_ARRAY[0:100].tolist()

    def test_data_bin_streams_over_limit(self):
        response = self._content(self._big_dataset_id(), "data", path="/big", format="bin")
        self._assert_status_code_is(response, 200)
        assert len(response.content) == 2_000_000
        assert int(response.headers["content-length"]) == 2_000_000
        assert response.content == BIG_ARRAY.tobytes()

    def test_data_npy_round_trips(self):
        response = self._content(self._big_dataset_id(), "data", path="/big", format="npy")
        self._assert_status_code_is(response, 200)
        loaded = np.load(io.BytesIO(response.content))
        assert loaded.shape == (2_000_000,)
        assert np.array_equal(loaded, BIG_ARRAY)

    def test_stats_incremental_over_limit(self):
        response = self._content(self._big_dataset_id(), "stats", path="/big")
        self._assert_status_code_is(response, 200)
        hvals = response.json()
        assert hvals["min"] == int(BIG_ARRAY.min())
        assert hvals["max"] == int(BIG_ARRAY.max())
        assert hvals["mean"] == int(BIG_ARRAY.mean())
        assert hvals["std"] == int(BIG_ARRAY.std())

    def test_data_invalid_selection_rejected(self):
        response = self._content(self._big_dataset_id(), "data", path="/big", selection="foo")
        self._assert_status_code_is(response, 400)

    def test_data_nonpositive_step_selection_rejected(self):
        response = self._content(self._big_dataset_id(), "data", path="/big", selection="0:10:0")
        self._assert_status_code_is(response, 400)

    def test_attr_over_limit_rejected(self):
        response = self._content(self._big_dataset_id(), "attr", path="/big")
        self._assert_status_code_is(response, 400)

    def test_data_vlen_under_cap(self):
        response = self._content(self._big_dataset_id(), "data", path="/small_vlen")
        self._assert_status_code_is(response, 200)
        assert len(response.json()) == 3

    def test_data_vlen_over_cap_rejected(self):
        response = self._content(self._big_dataset_id(), "data", path="/big_vlen")
        self._assert_status_code_is(response, 400)
