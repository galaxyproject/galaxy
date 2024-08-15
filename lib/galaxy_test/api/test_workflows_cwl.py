"""Test CWL workflow functionality."""

from galaxy_test.api.test_workflows import BaseWorkflowsApiTestCase
from galaxy_test.base.populators import CwlPopulator


class BaseCwlWorkflowsApiTestCase(BaseWorkflowsApiTestCase):
    allow_path_paste = True
    require_admin_user = True

    def setUp(self):
        super().setUp()
        self.cwl_populator = CwlPopulator(self.dataset_populator, self.workflow_populator)
