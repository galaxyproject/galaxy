"""Integration tests for the Pulsar embedded runner with remote metadata."""

import os

import pytest

from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
EMBEDDED_PULSAR_JOB_CONFIG_FILE = os.path.join(SCRIPT_DIRECTORY, "embedded_pulsar_metadata_extended_job_conf.yml")


class EmbeddedAndExtendedMetadataPulsarIntegrationInstance(integration_util.IntegrationInstance):
    """Describe a Galaxy test instance with embedded pulsar configured."""

    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["job_config_file"] = EMBEDDED_PULSAR_JOB_CONFIG_FILE
        config["object_store_store_by"] = "uuid"
        config["metadata_strategy"] = "extended"
        config["retry_metadata_internally"] = False


instance = integration_util.integration_module_instance(EmbeddedAndExtendedMetadataPulsarIntegrationInstance)

test_tools = integration_util.integration_tool_runner(
    [
        "version_command_plain",
        "version_command_tool_dir",
        "simple_constructs",
        "metadata_bam",
        "job_properties",
        "from_work_dir_glob",
        "gx_group_tag",
        "output_format",
        "create_directory_index",
    ]
)


@pytest.mark.skipif(os.geteuid() == 0, reason="root reads files without read permission, so the copy wouldn't fail")
def test_failed_directory_output_copy_fails_job(instance):
    populator = DatasetPopulator(instance.galaxy_interactor)
    history_id = populator.new_history()
    reference = populator.new_dataset(history_id, content=">seq\nACGT\n", file_type="fasta", wait=True)
    response = populator.run_tool(
        "create_directory_index_unreadable", {"reference": {"src": "hda", "id": reference["id"]}}, history_id
    )
    job_id = response["jobs"][0]["id"]
    populator.wait_for_job(job_id)

    job = populator.get_job_details(job_id, full=True).json()
    assert job["state"] == "error"
    assert "out_dir/./2.txt' for reading: Permission denied" in job["tool_stderr"]
