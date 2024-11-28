from typing import Literal

from galaxy.schema.schema import CreateWorkflowLandingRequestPayload
from .framework import (
    managed_history,
    RunsWorkflows,
    selenium_test,
    SeleniumTestCase,
)


class TestWorkflowLanding(SeleniumTestCase, RunsWorkflows):
    ensure_registered = True

    @selenium_test
    @managed_history
    def test_private_request(self):
        self._create_landing_and_run(public="false")

    @selenium_test
    @managed_history
    def test_pubblic_request(self):
        self._create_landing_and_run(public="true")

    def _create_landing_and_run(self, public: Literal["false", "true"]):
        self.perform_upload(self.get_filename("1.txt"))
        self.wait_for_history()
        workflow_id = self.workflow_populator.upload_yaml_workflow(
            """
class: GalaxyWorkflow
inputs:
  input_int: integer
  input_data: data
steps:
  simple_constructs:
    tool_id: simple_constructs
    label: tool_exec
    in:
      inttest: input_int
      files_0|file: input_data
""",
            name=self._get_random_name("landing_wf"),
        )
        if public == "true":
            client_secret = None
        else:
            client_secret = "abcdefg"
        landing_request_payload = CreateWorkflowLandingRequestPayload(
            workflow_id=workflow_id,
            workflow_target_type="stored_workflow",
            request_state={"input_int": 321123},
            public=public,
            client_secret=client_secret,
        )
        landing_request = self.dataset_populator.create_workflow_landing(landing_request_payload)
        self.go_to_workflow_landing(str(landing_request.uuid), public="false", client_secret=client_secret)
        self.screenshot("workflow_run_private_landing")
        self.workflow_run_submit()
        output_hid = 2
        self.workflow_run_wait_for_ok(hid=output_hid)
        history_id = self.current_history_id()
        content = self.dataset_populator.get_history_dataset_content(history_id, hid=output_hid)
        assert "321123" in content, content
