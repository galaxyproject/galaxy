"""Tool input paths on an embedded Pulsar destination with ``rewrite_parameters: true``.

With ``rewrite_parameters`` the Pulsar client leaves the command line and
config files alone, so every path a tool sees has to come from the job's
compute environment.
"""

import os

from galaxy import model
from galaxy.util.hash_util import md5_hash_file
from galaxy_test.base.populators import (
    DatasetCollectionPopulator,
    DatasetPopulator,
)
from galaxy_test.driver import integration_util

JOB_CONFIG = {
    "runners": {
        "local": {"load": "galaxy.jobs.runners.local:LocalJobRunner"},
        "pulsar_embed": {
            "load": "galaxy.jobs.runners.pulsar:PulsarEmbeddedJobRunner",
            "pulsar_app_config": {
                "tool_dependency_dir": "none",
                "conda_auto_init": False,
                "conda_auto_install": False,
            },
        },
    },
    "execution": {
        "default": "pulsar_embed",
        "environments": {
            "local": {"runner": "local"},
            "pulsar_embed": {
                "runner": "pulsar_embed",
                "default_file_action": "copy",
                "rewrite_parameters": True,
            },
        },
    },
    "tools": [{"id": "__DATA_FETCH__", "environment": "local"}],
}


class TestEmbeddedPulsarRewriteParameters(integration_util.IntegrationTestCase):
    framework_tool_and_types = True
    dataset_populator: DatasetPopulator
    dataset_collection_populator: DatasetCollectionPopulator

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.dataset_collection_populator = DatasetCollectionPopulator(self.galaxy_interactor)

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["job_config"] = JOB_CONFIG
        config["outputs_to_working_directory"] = False

    def test_collection_and_metadata_file_accessors_give_staged_paths(self) -> None:
        self._check_accessors(metadata_params=True)

    def test_metadata_file_accessors_stage_metadata_files_by_themselves(self) -> None:
        # Without $input.metadata.bam_index in the command, only the accessors can get
        # Pulsar to stage the metadata files.
        self._check_accessors(metadata_params=False)

    def _check_accessors(self, metadata_params: bool) -> None:
        with self.dataset_populator.test_history() as history_id:
            bams = [self.dataset_populator.new_bam_dataset(history_id, self.test_data_resolver) for _ in range(2)]
            single = self.dataset_populator.new_bam_dataset(history_id, self.test_data_resolver)
            hdca = self.dataset_collection_populator.create_list_in_history(
                history_id,
                direct_upload=False,
                element_identifiers=[{"name": f"e{i}", "src": "hda", "id": bam["id"]} for i, bam in enumerate(bams)],
                wait=True,
            ).json()
            job = (
                self.dataset_populator.describe_tool_execution("collection_input_paths")
                .in_history(history_id)
                .with_inputs(
                    {
                        "input1": {"src": "hdca", "id": hdca["id"]},
                        "single": {"src": "hda", "id": single["id"]},
                        "metadata_params": metadata_params,
                    }
                )
                .assert_has_single_job
            )
            out = job.with_output("out").contents
            json_out = job.with_output("json_out").json
        paths: dict[str, list[str]] = {}
        checksums: dict[str, str] = {}
        for line in out.splitlines():
            key, value = line.split(":", 1)
            if key == "CHECKSUM":
                checksum, path = value.split()
                checksums[path] = checksum
            else:
                paths[key] = value.split()
        assert ("COLL_FOR_METADATA_PARAM" in paths) == metadata_params

        # Every path the job got sits in Pulsar's staging directory next to the job's
        # working directory, and holds the bytes Galaxy has.
        job_directory = paths["JOB_DIRECTORY"][0]
        assert os.path.basename(job_directory) == "working", job_directory
        staging_directory = os.path.join(os.path.dirname(job_directory), "")
        hdas = [self._hda(bam["id"]) for bam in bams] + [self._hda(single["id"])]
        job_paths = paths["FOR_LOOP"] + paths["SINGLE"]
        job_metadata_paths = paths["COLL_ALL_METADATA_FILES"] + paths["SINGLE_ALL_METADATA_FILES"]
        assert len(job_paths) == len(job_metadata_paths) == 3, paths
        expected = [(hda.get_file_name(), job_path) for hda, job_path in zip(hdas, job_paths)] + [
            (hda.metadata.bam_index.get_file_name(), job_path) for hda, job_path in zip(hdas, job_metadata_paths)
        ]
        for galaxy_path, job_path in expected:
            assert job_path.startswith(staging_directory), (job_path, staging_directory)
            assert job_path in checksums, f"{job_path} was not staged"
            assert checksums[job_path] == md5_hash_file(galaxy_path), job_path

        equal_pairs = [
            ("ALL_PATHS", "FOR_LOOP"),
            ("COLL_SERIALIZE_SOURCE", "FOR_LOOP"),
            ("COLL_SERIALIZE_METADATA", "COLL_ALL_METADATA_FILES"),
            ("SINGLE_SERIALIZE_SOURCE", "SINGLE"),
            ("SINGLE_SERIALIZE_METADATA", "SINGLE_ALL_METADATA_FILES"),
        ]
        if metadata_params:
            equal_pairs += [
                ("COLL_FOR_METADATA_PARAM", "COLL_ALL_METADATA_FILES"),
                ("SINGLE_METADATA_PARAM", "SINGLE_ALL_METADATA_FILES"),
            ]
        for key, expected_key in equal_pairs:
            assert paths[key] == paths[expected_key], (key, paths[key], expected_key, paths[expected_key])
        assert json_out == {
            "input1": paths["FOR_LOOP"],
            "single": paths["SINGLE"][0],
            "metadata_params": metadata_params,
        }

    def _hda(self, encoded_id: str) -> model.HistoryDatasetAssociation:
        session = self._app.model.session
        session.expire_all()
        hda = session.get(model.HistoryDatasetAssociation, self._app.security.decode_id(encoded_id))
        assert hda is not None
        return hda
