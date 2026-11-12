"""Integration tests for the ``fail_invalid_validated_outputs`` option."""

from galaxy_test.base.populators import (
    DatasetPopulator,
    WorkflowPopulator,
)
from galaxy_test.base.workflow_fixtures import (
    TRUNCATED_LAV,
    WORKFLOW_VALIDATE_THEN_CAT,
)
from galaxy_test.driver import integration_util


class TestFailInvalidValidatedOutputs(integration_util.IntegrationTestCase):
    dataset_populator: DatasetPopulator

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.workflow_populator = WorkflowPopulator(self.galaxy_interactor)

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["fail_invalid_validated_outputs"] = True

    def test_invalid_output_is_errored_and_dependent_paused(self):
        workflow_id = self.workflow_populator.upload_yaml_workflow(WORKFLOW_VALIDATE_THEN_CAT)
        with self.dataset_populator.test_history() as history_id:
            hda1 = self.dataset_populator.new_dataset(history_id, content=TRUNCATED_LAV, file_type="lav", wait=True)
            invocation_id = self.workflow_populator.invoke_workflow(
                workflow_id, history_id=history_id, inputs={"0": {"src": "hda", "id": hda1["id"]}}
            ).json()["id"]
            self.workflow_populator.wait_for_workflow(workflow_id, invocation_id, history_id, assert_ok=False)
            validated = self.dataset_populator.get_history_dataset_details(
                history_id, hid=2, wait=True, assert_ok=False
            )
            assert validated["validated_state"] == "invalid", validated
            assert validated["state"] == "error", validated
            assert "#:eof" in validated["misc_info"], validated
            dependent = self.dataset_populator.get_history_dataset_details(
                history_id, hid=3, wait=True, assert_ok=False
            )
            assert dependent["state"] == "paused", dependent
