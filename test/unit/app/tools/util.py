from galaxy import model
from galaxy.app_unittest_utils.tools_support import UsesApp
from galaxy.tools.parameters import basic
from galaxy.util import XML
from galaxy.util.unittest import TestCase


class MockTool:
    def __init__(self, app):
        self.app = app
        self.tool_type = "default"
        self.valid_input_states = model.Dataset.valid_input_states
        self.profile = 23.0


class BaseParameterTestCase(TestCase, UsesApp):
    def setUp(self):
        self.setup_app()
        self.mock_tool = MockTool(self.app)

    def _parameter_for(self, **kwds):
        content = kwds["xml"]
        param_xml = XML(content)
        return basic.ToolParameter.build(self.mock_tool, param_xml)
