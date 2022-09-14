import os

from galaxy_test.base.populators import WorkflowPopulator
from ._framework import PerformanceTestCase

GALAXY_TEST_PERFORMANCE_TIMEOUT_DEFAULT = 5000
GALAXY_TEST_PERFORMANCE_TIMEOUT = int(
    os.environ.get("GALAXY_TEST_PERFORMANCE_TIMEOUT", GALAXY_TEST_PERFORMANCE_TIMEOUT_DEFAULT)
)
GALAXY_TEST_PERFORMANCE_COLLECTION_SIZE_DEFAULT = 4
GALAXY_TEST_PERFORMANCE_COLLECTION_SIZE = int(
    os.environ.get("GALAXY_TEST_PERFORMANCE_COLLECTION_SIZE", GALAXY_TEST_PERFORMANCE_COLLECTION_SIZE_DEFAULT)
)
GALAXY_TEST_PERFORMANCE_WORKFLOW_DEPTH_DEFAULT = 3
GALAXY_TEST_PERFORMANCE_WORKFLOW_DEPTH = int(
    os.environ.get("GALAXY_TEST_PERFORMANCE_WORKFLOW_DEPTH", GALAXY_TEST_PERFORMANCE_WORKFLOW_DEPTH_DEFAULT)
)


class WorkflowFrameworkPerformanceTestCase(PerformanceTestCase):
    framework_tool_and_types = True

    def setUp(self):
        super().setUp()
        self.workflow_populator = WorkflowPopulator(self.galaxy_interactor)

    def test_run_simple(self):
        self._run_performance_workflow("simple")

    def test_run_wave(self):
        self._run_performance_workflow("wave_simple")

    def test_run_two_output(self):
        self._run_performance_workflow("two_output")

    def _run_performance_workflow(self, workflow_type):
        workflow_yaml = self.workflow_populator.scaling_workflow_yaml(
            workflow_type=workflow_type,
            collection_size=GALAXY_TEST_PERFORMANCE_COLLECTION_SIZE,
            workflow_depth=GALAXY_TEST_PERFORMANCE_WORKFLOW_DEPTH,
        )
        run_summary = self.workflow_populator.run_workflow(
            workflow_yaml,
            test_data={},
            wait=False,
        )
        self.workflow_populator.wait_for_workflow(
            run_summary.workflow_id,
            run_summary.invocation_id,
            run_summary.history_id,
            assert_ok=True,
            timeout=GALAXY_TEST_PERFORMANCE_TIMEOUT,
        )
