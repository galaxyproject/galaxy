"""Tool input paths on an embedded Pulsar destination with ``rewrite_parameters: true``.

With ``rewrite_parameters`` the Pulsar client leaves the command line and
config files alone, so every path a tool sees has to come from the job's
compute environment.
"""

import base64
import os
from typing import Any

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

    def test_collection_and_metadata_file_accessors_give_staged_paths(self):
        with self.dataset_populator.test_history() as history_id:
            single = self.dataset_populator.new_bam_dataset(history_id, self.test_data_resolver)
            hdca = self._upload_bam_list(history_id, ["e1", "e2"])
            job = (
                self.dataset_populator.describe_tool_execution("collection_input_paths")
                .in_history(history_id)
                .with_inputs(
                    {"input1": {"src": "hdca", "id": hdca["id"]}, "single": {"src": "hda", "id": single["id"]}}
                )
                .assert_has_single_job
            )
            out = job.with_output("out").contents
            json_out = job.with_output("json_out").json
        paths = {key: value.split() for key, value in (line.split(":", 1) for line in out.splitlines())}
        # Element and metadata parameter wrappers already go through the compute
        # environment; check they point at Pulsar's staged copies next to the job's
        # working directory.
        job_directory = paths["JOB_DIRECTORY"][0]
        assert os.path.basename(job_directory) == "working", job_directory
        staging_directory = os.path.join(os.path.dirname(job_directory), "")
        for key, count in (
            ("FOR_LOOP", 2),
            ("COLL_FOR_METADATA_PARAM", 2),
            ("SINGLE", 1),
            ("SINGLE_METADATA_PARAM", 1),
        ):
            assert len(paths[key]) == count, (key, paths[key])
            assert all(p.startswith(staging_directory) for p in paths[key]), (key, paths[key], staging_directory)
        for key, expected in (
            ("ALL_PATHS", "FOR_LOOP"),
            ("COLL_SERIALIZE_SOURCE", "FOR_LOOP"),
            ("COLL_ALL_METADATA_FILES", "COLL_FOR_METADATA_PARAM"),
            ("COLL_SERIALIZE_METADATA", "COLL_FOR_METADATA_PARAM"),
            ("SINGLE_SERIALIZE_SOURCE", "SINGLE"),
            ("SINGLE_ALL_METADATA_FILES", "SINGLE_METADATA_PARAM"),
            ("SINGLE_SERIALIZE_METADATA", "SINGLE_METADATA_PARAM"),
        ):
            assert paths[key] == paths[expected], (key, paths[key], expected, paths[expected])
        assert json_out == {"input1": paths["FOR_LOOP"], "single": paths["SINGLE"][0]}

    def _upload_bam_list(self, history_id: str, identifiers: list[str]) -> dict[str, Any]:
        bam_url = "base64://" + base64.b64encode(self.test_data_resolver.get_filecontent("1.bam")).decode()
        elements = [{"src": "url", "url": bam_url, "ext": "bam", "name": identifier} for identifier in identifiers]
        response = self.dataset_collection_populator.upload_collection(history_id, "list", elements=elements, wait=True)
        hdca: dict[str, Any] = response.json()["output_collections"][0]
        return hdca
