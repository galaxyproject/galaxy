"""Materialize deferred directory datasets inside the job, with remote tool evaluation."""

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from galaxy.model.unittest_utils.zarr_fixtures import write_zarr_v3_store
from galaxy.util.unittest_utils.test_http_server import serve_directory
from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util
from galaxy_test.driver.driver_util import FRAMEWORK_SAMPLE_TOOLS_CONF


@pytest.fixture
def zarr_store_url(tmp_path: Path) -> Iterator[str]:
    """Serve a consolidated Zarr v3 store over plain HTTP, which cannot list directories."""
    write_zarr_v3_store(tmp_path / "store.zarr")
    with serve_directory(tmp_path) as base_url:
        yield f"{base_url}/store.zarr"


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
        assert listing.splitlines() == ["./arr/c/0", "./arr/zarr.json", "./zarr.json"]
