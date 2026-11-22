"""Path accessors give tools compute-side paths on embedded Pulsar with ``rewrite_parameters: true``."""

import json
import os

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

    def test_accessors_match_per_element_paths(self, history_id: str) -> None:
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
            {"input1": {"src": "hdca", "id": hdca["id"]}, "single": {"src": "hda", "id": single["id"]}},
            history_id,
        )
        self.dataset_populator.wait_for_job(run["jobs"][0]["id"], assert_ok=True)
        content = self.dataset_populator.get_history_dataset_content(history_id, dataset_id=run["outputs"][0]["id"])
        lines = dict(line.split(":", 1) for line in content.splitlines() if line)
        paths = {key: value.split() for key, value in lines.items() if key != "JSON_PATHS_CONFIGFILE"}

        # Pulsar staged the inputs next to the job's working directory.
        staging_directory = os.path.dirname(paths["JOB_DIRECTORY"][0])
        for path in paths["FOR_LOOP"] + paths["COLL_FOR_METADATA_PARAM"] + paths["SINGLE_METADATA_PARAM"]:
            assert path.startswith(staging_directory + os.sep), path

        assert len(paths["FOR_LOOP"]) == 2
        assert paths["ALL_PATHS"] == paths["FOR_LOOP"]
        assert paths["COLL_SERIALIZE_SOURCE"] == paths["FOR_LOOP"]
        assert len(paths["COLL_FOR_METADATA_PARAM"]) == 2
        assert paths["COLL_ALL_METADATA_FILES"] == paths["COLL_FOR_METADATA_PARAM"]
        assert paths["COLL_SERIALIZE_METADATA"] == paths["COLL_FOR_METADATA_PARAM"]
        assert paths["SINGLE_SERIALIZE_SOURCE"] == paths["SINGLE"]
        assert paths["SINGLE_ALL_METADATA_FILES"] == paths["SINGLE_METADATA_PARAM"]
        assert paths["SINGLE_SERIALIZE_METADATA"] == paths["SINGLE_METADATA_PARAM"]
        json_paths = json.loads(lines["JSON_PATHS_CONFIGFILE"])
        assert json_paths == {"input1": paths["FOR_LOOP"], "single": paths["SINGLE"][0]}
