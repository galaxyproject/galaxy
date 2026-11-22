"""Path accessors give tools compute-side paths on embedded Pulsar with ``rewrite_parameters: true``."""

import json
import os

from galaxy import model
from galaxy.util.hash_util import md5_hash_file
from galaxy_test.base.populators import (
    DatasetCollectionPopulator,
    DatasetPopulator,
)
from galaxy_test.driver import integration_util

PULSAR_APP_CONFIG = {
    "tool_dependency_dir": "none",
    "conda_auto_init": False,
    "conda_auto_install": False,
}


class TestEmbeddedPulsarComputeSidePaths(integration_util.IntegrationTestCase):
    dataset_populator: DatasetPopulator
    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config.pop("job_config_file", None)
        config["job_config"] = {
            "runners": {
                "local": {"load": "galaxy.jobs.runners.local:LocalJobRunner"},
                "pulsar_embed": {
                    "load": "galaxy.jobs.runners.pulsar:PulsarEmbeddedJobRunner",
                    "pulsar_app_config": dict(PULSAR_APP_CONFIG),
                },
            },
            "execution": {
                "default": "local",
                "environments": {
                    "local": {"runner": "local"},
                    "pulsar_embed": {
                        "runner": "pulsar_embed",
                        "default_file_action": "copy",
                        "rewrite_parameters": True,
                    },
                },
            },
            "tools": [{"id": "collection_paths_echo", "environment": "pulsar_embed"}],
        }

    def setUp(self) -> None:
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.dataset_collection_populator = DatasetCollectionPopulator(self.galaxy_interactor)

    def test_accessors_give_staged_paths(self, history_id: str) -> None:
        self._check_accessors(history_id, metadata_params=True)

    def test_accessors_stage_metadata_files_by_themselves(self, history_id: str) -> None:
        # Pulsar stages only the metadata files the job asked the compute environment for,
        # so without $input.metadata.bam_index only the accessors can get them staged.
        self._check_accessors(history_id, metadata_params=False)

    def _check_accessors(self, history_id: str, metadata_params: bool) -> None:
        bams = [self.dataset_populator.new_bam_dataset(history_id, self.test_data_resolver) for _ in range(2)]
        single = self.dataset_populator.new_bam_dataset(history_id, self.test_data_resolver)
        hdca = self.dataset_collection_populator.create_list_in_history(
            history_id,
            direct_upload=False,
            element_identifiers=[{"name": f"element{i}", "src": "hda", "id": bam["id"]} for i, bam in enumerate(bams)],
            wait=True,
        ).json()
        run = self.dataset_populator.run_tool(
            "collection_paths_echo",
            {
                "input1": {"src": "hdca", "id": hdca["id"]},
                "single": {"src": "hda", "id": single["id"]},
                "metadata_params": metadata_params,
            },
            history_id,
        )
        self.dataset_populator.wait_for_job(run["jobs"][0]["id"], assert_ok=True)
        content = self.dataset_populator.get_history_dataset_content(history_id, dataset_id=run["outputs"][0]["id"])
        lines: dict[str, str] = {}
        checksums: dict[str, str] = {}
        for line in content.splitlines():
            key, value = line.split(":", 1)
            if key == "CHECKSUM":
                checksum, path = value.split()
                checksums[path] = checksum
            else:
                lines[key] = value
        paths = {key: value.split() for key, value in lines.items() if not key.startswith("JSON_")}

        assert len(paths["FOR_LOOP"]) == 2
        assert paths["ALL_PATHS"] == paths["FOR_LOOP"]
        assert paths["COLL_SERIALIZE_SOURCE"] == paths["FOR_LOOP"]
        assert len(paths["COLL_ALL_METADATA_FILES"]) == 2
        assert paths["COLL_SERIALIZE_METADATA"] == paths["COLL_ALL_METADATA_FILES"]
        assert paths["SINGLE_SERIALIZE_SOURCE"] == paths["SINGLE"]
        assert len(paths["SINGLE_ALL_METADATA_FILES"]) == 1
        assert paths["SINGLE_SERIALIZE_METADATA"] == paths["SINGLE_ALL_METADATA_FILES"]
        if metadata_params:
            assert paths["COLL_FOR_METADATA_PARAM"] == paths["COLL_ALL_METADATA_FILES"]
            assert paths["SINGLE_METADATA_PARAM"] == paths["SINGLE_ALL_METADATA_FILES"]
        json_paths = json.loads(lines["JSON_PATHS_CONFIGFILE"])
        assert json_paths["input1"] == paths["FOR_LOOP"]
        assert json_paths["single"] == paths["SINGLE"][0]

        # Pulsar staged every file next to the job's working directory, and the job read
        # the same bytes there that Galaxy holds.
        staging_directory = os.path.dirname(paths["JOB_DIRECTORY"][0])
        hdas = [self._hda(bam["id"]) for bam in bams] + [self._hda(single["id"])]
        job_paths = paths["FOR_LOOP"] + paths["SINGLE"]
        job_metadata_paths = paths["COLL_ALL_METADATA_FILES"] + paths["SINGLE_ALL_METADATA_FILES"]
        expected = [(hda.get_file_name(), job_path) for hda, job_path in zip(hdas, job_paths)] + [
            (hda.metadata.bam_index.get_file_name(), job_path) for hda, job_path in zip(hdas, job_metadata_paths)
        ]
        for galaxy_path, job_path in expected:
            assert job_path.startswith(staging_directory + os.sep), job_path
            assert job_path in checksums, f"{job_path} was not staged"
            assert checksums[job_path] == md5_hash_file(galaxy_path), job_path

    def _hda(self, encoded_id: str) -> model.HistoryDatasetAssociation:
        session = self._app.model.session
        session.expire_all()
        hda = session.get(model.HistoryDatasetAssociation, self._app.security.decode_id(encoded_id))
        assert hda is not None
        return hda
