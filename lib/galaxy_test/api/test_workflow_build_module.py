from galaxy_test.base.populators import (
    skip_without_tool,
    WorkflowPopulator,
)
from ._framework import ApiTestCase


class TestBuildWorkflowModule(ApiTestCase):

    def setUp(self):
        super().setUp()
        self.workflow_populator = WorkflowPopulator(self.galaxy_interactor)

    @skip_without_tool("select_from_url")
    def test_build_module_filter_dynamic_select(self):
        # Verify that filtering on parameters that depend on parameter and validators works
        # fine in workflow building mode.
        module = self.workflow_populator.build_module(step_type="tool", content_id="select_from_url")
        assert not module["errors"], module["errors"]
