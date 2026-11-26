import time
from unittest import mock

from galaxy.tools import ExpressionTool
from galaxy_test.base.api import UsesCeleryTasks
from galaxy_test.base.populators import (
    DatasetPopulator,
    WorkflowPopulator,
)
from galaxy_test.driver import integration_util

PICK_VALUE_CHANGE_DATATYPE_INTO_CAT = """
class: GalaxyWorkflow
inputs:
  input1:
    type: data
steps:
  pick_value:
    tool_id: pick_value
    in:
      style_cond|type_cond|pick_from_0|value:
        source: input1
    out:
      data_param:
        change_datatype: tabular
    tool_state:
      style_cond:
        pick_style: first_or_error
        type_cond:
          param_type: data
          pick_from:
          - value:
              __class__: RuntimeValue
  cat:
    tool_id: cat1
    in:
      input1: pick_value/data_param
outputs:
  pick_out:
    outputSource: pick_value/data_param
  cat_out:
    outputSource: cat/out_file1
"""

TABULAR_CONTENT = "1\t2\t3\n4\t5\t6\n"


class TestExpressionToolFinishExtendedMetadataIntegration(integration_util.IntegrationTestCase, UsesCeleryTasks):
    dataset_populator: DatasetPopulator
    workflow_populator: WorkflowPopulator
    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["metadata_strategy"] = "extended"
        UsesCeleryTasks.handle_galaxy_config_kwds(config)

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.workflow_populator = WorkflowPopulator(self.galaxy_interactor)

    def test_changed_datatype_output_not_consumed_before_metadata_is_set(self):
        observed_during_finish = []
        exec_after_process = ExpressionTool.exec_after_process

        def observe_then_exec_after_process(tool, app, inp_data, out_data, param_dict, job, final_job_state=None):
            # Runs inside JobWrapper.finish, after the outputs are collected and before the
            # final commit. Record what API clients and the job handler see at this point.
            output_id = app.security.encode_id(out_data["data_param"].id)
            history_id = app.security.encode_id(job.history_id)
            observed = self._get(f"datasets/{output_id}").json()
            observed_during_finish.append(observed)
            if observed["state"] == "ok":
                # Give the job handler time to dispatch the consumer of this output.
                deadline = time.time() + 20
                while time.time() < deadline:
                    jobs = self._get("jobs", {"history_id": history_id, "tool_id": "cat1"}).json()
                    if jobs and jobs[0]["state"] in ("ok", "error"):
                        break
                    time.sleep(0.5)
            return exec_after_process(
                tool, app, inp_data, out_data, param_dict, job=job, final_job_state=final_job_state
            )

        with self.dataset_populator.test_history() as history_id:
            with mock.patch.object(ExpressionTool, "exec_after_process", observe_then_exec_after_process):
                summary = self.workflow_populator.run_workflow(
                    PICK_VALUE_CHANGE_DATATYPE_INTO_CAT,
                    test_data={"input1": {"content": TABULAR_CONTENT, "type": "File", "file_type": "txt"}},
                    history_id=history_id,
                )
            invocation = self.workflow_populator.get_invocation(summary.invocation_id)
            cat_out = self.dataset_populator.get_history_dataset_content(
                history_id, content_id=invocation["outputs"]["cat_out"]["id"]
            )
            assert cat_out == TABULAR_CONTENT
            pick_out = self.dataset_populator.get_history_dataset_details(
                history_id, content_id=invocation["outputs"]["pick_out"]["id"]
            )
            assert pick_out["file_ext"] == "tabular"
            assert pick_out["metadata_columns"] == 3
            assert len(observed_during_finish) == 1
            observed = observed_during_finish[0]
            assert observed["state"] != "ok", observed
