"""Integration test for OS-level isolation of workflow expression evaluation.

Runs a workflow whose step ``when`` is a full JavaScript expression with
``expression_evaluation_isolation_command = "bubblewrap"``, so the expression is
evaluated out-of-process inside a bubblewrap jail during scheduling. A bare
``$(inputs.x)`` reference would resolve in pure Python and never reach the jailed
worker, so the ``when`` here is a ``${ ... }`` body that must go through the engine.

Skipped unless the ``bwrap`` binary is available (Linux CI installs bubblewrap); on
platforms without it the isolation falls back to in-process evaluation.
"""

import subprocess
import sys

import pytest

from galaxy.tools.expressions.js_engine import resolve_isolation_command
from galaxy_test.base.populators import (
    DatasetPopulator,
    WorkflowPopulator,
)
from galaxy_test.driver.integration_util import IntegrationTestCase


def _bwrap_can_sandbox() -> bool:
    # bubblewrap must be installed AND able to set up its sandbox here; namespace/
    # uid-map/exec can be blocked on locked-down hosts and CI runners.
    command = resolve_isolation_command("bubblewrap")
    if not command:
        return False
    try:
        proc = subprocess.run([*command, sys.executable, "-c", ""], capture_output=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return False
    return proc.returncode == 0


needs_bwrap = pytest.mark.skipif(
    not _bwrap_can_sandbox(),
    reason="bubblewrap not installed or cannot set up a sandbox in this environment",
)

WORKFLOW_WITH_JS_WHEN = """class: GalaxyWorkflow
inputs:
  should_run:
    type: boolean
  some_file:
    type: data
steps:
  cat1:
    tool_id: cat1
    in:
      input1: some_file
      should_run: should_run
    when: ${ return inputs.should_run; }
"""

TEST_DATA_SKIP = """
some_file:
  value: 1.bed
  type: File
should_run:
  value: false
  type: raw
"""

TEST_DATA_RUN = """
some_file:
  value: 1.bed
  type: File
should_run:
  value: true
  type: raw
"""


class TestExpressionEvaluationIsolationIntegration(IntegrationTestCase):
    dataset_populator: DatasetPopulator
    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["expression_evaluation_isolation_command"] = "bubblewrap"

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.workflow_populator = WorkflowPopulator(self.galaxy_interactor)

    def _cat1_jobs(self, invocation_id):
        invocation = self.workflow_populator.get_invocation(invocation_id, step_details=True)
        return [
            job for step in invocation["steps"] if step["workflow_step_label"] == "cat1" for job in step["jobs"]
        ], invocation

    @needs_bwrap
    def test_when_false_skips_step_via_bubblewrap(self):
        # The jailed worker must evaluate the JS `when` to false and skip the step.
        with self.dataset_populator.test_history() as history_id:
            summary = self.workflow_populator.run_workflow(
                WORKFLOW_WITH_JS_WHEN, test_data=TEST_DATA_SKIP, history_id=history_id
            )
            jobs, invocation = self._cat1_jobs(summary.invocation_id)
            assert sum(1 for job in jobs if job["state"] == "skipped") == 1, invocation

    @needs_bwrap
    def test_when_true_runs_step_via_bubblewrap(self):
        # The jailed worker must evaluate the JS `when` to true so the step runs.
        with self.dataset_populator.test_history() as history_id:
            summary = self.workflow_populator.run_workflow(
                WORKFLOW_WITH_JS_WHEN, test_data=TEST_DATA_RUN, history_id=history_id
            )
            jobs, invocation = self._cat1_jobs(summary.invocation_id)
            assert jobs, invocation
            assert not any(job["state"] == "skipped" for job in jobs), invocation
