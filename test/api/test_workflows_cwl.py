"""Test CWL workflow functionality."""
import os

from galaxy.util import galaxy_root_path

from .test_workflows import BaseWorkflowsApiTestCase

cwl_tool_directory = os.path.join(galaxy_root_path, "test", "functional", "tools", "cwl_tools")


class CwlWorkflowsTestCase( BaseWorkflowsApiTestCase ):
    """Test case encompassing CWL workflow tests."""

    def test_count_lines_wf1( self ):
        """Test simple workflow count-lines1-wf.cwl."""
        load_response = self._load_workflow("draft3/count-lines1-wf.cwl")
        self._assert_status_code_is( load_response, 200 )

    def _load_workflow(self, rel_path):
        path = os.path.join(cwl_tool_directory, rel_path)
        data = dict(
            from_path=path,
        )
        route = "workflows"
        upload_response = self._post( route, data=data, admin=True )
        return upload_response
