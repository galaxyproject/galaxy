from unittest import TestCase
from xml.etree.ElementTree import XML

from galaxy import model
from galaxy.tools.parameters import basic
from galaxy.util import bunch
from ..tools_support import UsesApp


class BaseParameterTestCase(TestCase, UsesApp):

    def setUp(self):
        self.setup_app()
        self.mock_tool = bunch.Bunch(
            app=self.app,
            tool_type="default",
            valid_input_states=model.Dataset.valid_input_states,
        )

    def _parameter_for(self, **kwds):
        content = kwds["xml"]
        param_xml = XML(content)
        return basic.ToolParameter.build(self.mock_tool, param_xml)
