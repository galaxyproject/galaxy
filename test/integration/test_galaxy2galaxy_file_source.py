"""A user's own galaxy2galaxy file source, pointed back at this Galaxy."""

import uuid

import pytest

from galaxy.files.templates.examples import get_example
from galaxy_test.base.populators import (
    DatasetCollectionPopulator,
    DatasetPopulator,
)
from galaxy_test.driver import integration_util

pytest.importorskip("galaxy_fsspec")

BED = "chr1\t1\t10\n"


class TestGalaxy2GalaxyFileSourceIntegration(
    integration_util.IntegrationTestCase,
    integration_util.ConfiguresFileSourceTemplates,
    integration_util.ConfiguresDatabaseVault,
):
    dataset_populator: DatasetPopulator

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        cls._configure_database_vault(config)
        cls._configure_file_source_template_catalog(get_example("production_galaxy2galaxy.yml"), config)
        # The "other" Galaxy is this one, on a loopback address the plugin otherwise refuses.
        config["fetch_url_allowlist"] = ["127.0.0.0/8", "::1"]

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.collection_populator = DatasetCollectionPopulator(self.galaxy_interactor)

    def test_browse_and_import_from_a_history(self):
        name = f"g2g {uuid.uuid4().hex[:8]}"
        history_id = self.dataset_populator.new_history(name)
        self.dataset_populator.new_dataset(history_id, content=BED, name="regions.bed", file_type="bed", wait=True)
        self.collection_populator.create_pair_in_history(history_id, name="sample1", wait=True)
        history = f"{self._create_source()}/histories/{name}"

        entries = {entry["name"]: entry for entry in self._list(history)}
        assert sorted(entries) == ["regions.bed", "sample1"]
        assert entries["regions.bed"]["size"] == len(BED)
        assert sorted(entry["name"] for entry in self._list(f"{history}/sample1")) == ["forward", "reverse"]
        missing = self._get("remote_files", data={"target": f"{history}/no-such-dataset"})
        assert missing.status_code == 404

        target_history_id = self.dataset_populator.new_history()
        self.dataset_populator.fetch_hdas(target_history_id, [{"src": "url", "url": f"{history}/regions.bed"}])
        assert self.dataset_populator.get_history_dataset_content(target_history_id) == BED

    def _create_source(self) -> str:
        payload = {
            "name": "This Galaxy",
            "template_id": "galaxy2galaxy",
            "template_version": 0,
            "variables": {"base_url": self.url.rstrip("/"), "show_hid_in_names": False},
            "secrets": {"api_key": self.galaxy_interactor.api_key},
        }
        response = self._post("file_source_instances", data=payload, json=True)
        response.raise_for_status()
        return response.json()["uri_root"]

    def _list(self, target: str) -> list[dict]:
        response = self._get("remote_files", data={"target": target})
        response.raise_for_status()
        return response.json()
