import time

from galaxy_test.base.populators import (
    DatasetPopulator,
    WorkflowPopulator,
)
from galaxy_test.driver import integration_util


class TestFailJobWhenToolUnavailable(integration_util.IntegrationTestCase):
    dataset_populator: DatasetPopulator
    require_admin_user = True

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.workflow_populator = WorkflowPopulator(self.galaxy_interactor)

    @classmethod
    def handle_galaxy_config_kwds(
        cls,
        config,
    ):
        super().handle_galaxy_config_kwds(config)
        # config["jobs_directory"] = cls.jobs_directory
        # Disable tool dependency resolution.
        config["tool_dependency_dir"] = "none"

    def test_fail_job_when_tool_unavailable(self, history_id: str):
        self.workflow_populator.run_workflow(
            """
class: GalaxyWorkflow
inputs:
  input1:
    type: data
steps:
  sleep:
    tool_id: cat_data_and_sleep
    state:
      sleep_time: 10
      input1:
        $link: input1
  cat:
    tool_id: cat1
    state:
      input1:
        $link: sleep/out_file1
      queries:
        input2:
          $link: sleep/out_file1
test_data:
  input1: "hello world"
""",
            history_id=history_id,
            assert_ok=False,
            wait=False,
        )
        # Wait until workflow is fully scheduled, otherwise can't test effect of removing tool from queued job
        time.sleep(5)
        self._app.toolbox.remove_tool_by_id("cat1")
        self.dataset_populator.wait_for_history(history_id, assert_ok=False)
        state_details = self.galaxy_interactor.get(f"histories/{history_id}").json()["state_details"]
        assert state_details["running"] == 0
        assert state_details["ok"] == 2
        assert state_details["error"] == 1
        failed_hda = self.dataset_populator.get_history_dataset_details(
            history_id=history_id, assert_ok=False, details=True
        )
        assert failed_hda["state"] == "error"
        job = self.galaxy_interactor.get("jobs/{}".format(failed_hda["creating_job"])).json()
        assert job["state"] == "error"
