"""Materialize deferred directory datasets inside the job, with remote tool evaluation."""

import functools
import json
import os
import threading
from collections.abc import Iterator
from http.server import (
    SimpleHTTPRequestHandler,
    ThreadingHTTPServer,
)
from pathlib import Path
from typing import Any

import pytest

from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util
from galaxy_test.driver.driver_util import FRAMEWORK_SAMPLE_TOOLS_CONF

ZARR_ARRAY_METADATA: dict[str, Any] = {
    "zarr_format": 3,
    "node_type": "array",
    "shape": [3],
    "data_type": "uint8",
    "chunk_grid": {"name": "regular", "configuration": {"chunk_shape": [2]}},
    "chunk_key_encoding": {"name": "default", "configuration": {"separator": "/"}},
    "fill_value": 0,
    "codecs": [{"name": "bytes"}],
}


@pytest.fixture
def zarr_store_url(tmp_path: Path) -> Iterator[str]:
    """Serve a consolidated Zarr v3 store over plain HTTP, which cannot list directories."""
    store = tmp_path / "store.zarr"
    (store / "arr" / "c").mkdir(parents=True)
    group = {
        "zarr_format": 3,
        "node_type": "group",
        "attributes": {},
        "consolidated_metadata": {"kind": "inline", "must_understand": False, "metadata": {"arr": ZARR_ARRAY_METADATA}},
    }
    (store / "zarr.json").write_text(json.dumps(group))
    (store / "arr" / "zarr.json").write_text(json.dumps(ZARR_ARRAY_METADATA))
    # Only the first chunk is stored, the second holds just the fill value.
    (store / "arr" / "c" / "0").write_bytes(b"\x01\x02")

    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(tmp_path)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}/store.zarr"
    finally:
        server.shutdown()


class TestRemoteDeferredDirectoryMaterialization(integration_util.IntegrationTestCase):
    dataset_populator: DatasetPopulator
    # Framework tools with the stock datatypes, which include zarr.
    default_tool_conf = FRAMEWORK_SAMPLE_TOOLS_CONF

    def setUp(self) -> None:
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    @classmethod
    def handle_galaxy_config_kwds(cls, config: dict[str, Any]) -> None:
        super().handle_galaxy_config_kwds(config)
        # Evaluate the tool, and so materialize deferred inputs, in the job rather than the job handler.
        config["tool_evaluation_strategy"] = "remote"
        config["metadata_strategy"] = "extended"
        config["object_store_store_by"] = "uuid"
        config["retry_metadata_internally"] = False

    def test_deferred_zarr_is_materialized_in_the_job(self, zarr_store_url: str) -> None:
        history_id = self.dataset_populator.new_history()
        deferred_zarr = self.dataset_populator.create_deferred_hda(history_id, zarr_store_url, ext="zarr")
        inputs = {"input": {"src": "hda", "id": deferred_zarr["id"]}}

        run_response = self.dataset_populator.run_tool("directory_listing", inputs=inputs, history_id=history_id)
        self.dataset_populator.wait_for_job(run_response["jobs"][0]["id"], assert_ok=True)

        listing = self.dataset_populator.get_history_dataset_content(history_id, dataset=run_response["outputs"][0])
        assert listing.splitlines() == [
            os.path.join(".", "arr", "c", "0"),
            os.path.join(".", "arr", "zarr.json"),
            os.path.join(".", "zarr.json"),
        ]
