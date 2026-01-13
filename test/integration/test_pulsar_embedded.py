"""Integration tests for the Pulsar embedded runner."""

import os

from sqlalchemy import select

from galaxy import model
from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
EMBEDDED_PULSAR_JOB_CONFIG_FILE = os.path.join(SCRIPT_DIRECTORY, "embedded_pulsar_job_conf.yml")


class TestEmbeddedPulsarIntegrationInstance(integration_util.IntegrationTestCase):
    """Describe a Galaxy test instance with embedded pulsar configured."""

    framework_tool_and_types = True
    dataset_populator: DatasetPopulator

    def setUp(self) -> None:
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["job_config_file"] = EMBEDDED_PULSAR_JOB_CONFIG_FILE
        config["enable_celery_tasks"] = False
        config["metadata_strategy"] = "directory"
        config["cleanup_job"] = "never"

    def test_tool_eval_failure(self):
        with self.dataset_populator.test_history() as history_id:
            dataset = self.dataset_populator.new_dataset(history_id=history_id, content="ABC", ext="tabular")
            self.dataset_populator.run_tool(
                "gx_data_column",
                inputs={"ref_parameter": {"src": "hda", "id": dataset["id"]}, "parameter": 2},
                history_id=history_id,
            )
            failed_dataset = self.dataset_populator.get_history_dataset_details(history_id, wait=True, assert_ok=False)
            assert failed_dataset["state"] == "error"
            assert failed_dataset["misc_info"] == "Parameter 'parameter': requires a value, but no legal values defined"

    def test_collection_directory_discovery_does_not_collect_working_dir_files(self):
        """Test that collection discovery with directory attribute doesn't collect files from working directory root."""
        with self.dataset_populator.test_history() as history_id:
            # Create input dataset
            input_content = "101\t1\n101\t2\n101\t3\n1334\t1\n1334\t10\n1334\t11\n1334\t12\n1334\t13\n1334\t2\n"
            dataset = self.dataset_populator.new_dataset(history_id=history_id, content=input_content, ext="tabular")

            # Run the tool
            run_response = self.dataset_populator.run_tool(
                "collection_split_on_column",
                inputs={"input1": {"src": "hda", "id": dataset["id"]}},
                history_id=history_id,
            )

            # Wait for job to complete
            self.dataset_populator.wait_for_job(run_response["jobs"][0]["id"])

            # Get the job from the database
            job_id = run_response["jobs"][0]["id"]
            job_id_decoded = self._app.security.decode_id(job_id)

            sa_session = self._app.model.session
            job = sa_session.scalars(select(model.Job).filter_by(id=job_id_decoded)).one()

            # Get the job working directory using the object store
            job_working_directory = self._app.object_store.get_filename(
                job, base_dir="job_work", dir_only=True, obj_dir=True
            )
            assert job_working_directory is not None, "Could not determine job working directory"

            # Verify that do_not_collect_me.txt does NOT exist in the Galaxy job working directory
            # This file is created in the working directory but should not be staged back because
            # the collection discovery specifies directory="outputs"
            do_not_collect_path = os.path.join(job_working_directory, "working", "do_not_collect_me.txt")
            assert not os.path.exists(do_not_collect_path), (
                f"File {do_not_collect_path} should not have been collected from Pulsar, "
                "but it exists in Galaxy's job working directory"
            )


instance = integration_util.integration_module_instance(TestEmbeddedPulsarIntegrationInstance)

test_tools = integration_util.integration_tool_runner(
    [
        "cat_default",
        "cat_user_defined",
        "collection_nested_default",
        "collection_creates_dynamic_nested_from_json",
        "composite",
        "simple_constructs",
        "multi_data_param",
        "output_filter",
        "vcf_bgzip_test",
        "environment_variables",
        "multi_output_assign_primary_ext_dbkey",
        "job_properties",
        "strict_shell",
        "tool_provided_metadata_9",
        "simple_constructs_y",
        "composite_output",
        "composite_output_tests",
        "detect_errors",
        "tool_directory_copy",
        "metadata_columns",
        "create_directory_index",
        "collection_split_on_column",
    ]
)
