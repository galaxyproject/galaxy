from galaxy_test.api.test_workflows import ChangeDatatypeTests
from galaxy_test.base.populators import (
    DatasetPopulator,
    WorkflowPopulator,
)
from galaxy_test.driver import integration_util


def pin_directory_metadata(config):
    # Extended metadata can't store discovered outputs by id, they only get their id when Galaxy
    # imports them. A destination metadata_strategy wins over GALAXY_CONFIG_OVERRIDE_METADATA_STRATEGY,
    # which the weekly scheduled CI run sets to extended.
    config.pop("job_config_file", None)
    config["job_config"] = {
        "runners": {"local": {"load": "galaxy.jobs.runners.local:LocalJobRunner"}},
        "execution": {
            "default": "local",
            "environments": {"local": {"runner": "local", "metadata_strategy": "directory"}},
        },
    }


class TestChangeDatatypeStoreByIdIntegration(integration_util.IntegrationTestCase, ChangeDatatypeTests):
    """Test changing datatype with object_store_store_by: id."""

    dataset_populator: DatasetPopulator
    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["object_store_store_by"] = "id"
        config["retry_metadata_internally"] = False
        pin_directory_metadata(config)

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.workflow_populator = WorkflowPopulator(self.galaxy_interactor)


class StoreByIdIntegrationInstance(integration_util.IntegrationInstance):
    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["object_store_store_by"] = "id"
        config["outputs_to_working_directory"] = True
        pin_directory_metadata(config)


instance = integration_util.integration_module_instance(StoreByIdIntegrationInstance)

test_tools = integration_util.integration_tool_runner(
    [
        "composite_output_tests",
    ]
)
