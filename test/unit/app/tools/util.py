from typing import (
    cast,
    TYPE_CHECKING,
)

from galaxy import model
from galaxy.app_unittest_utils.tools_support import UsesApp
from galaxy.tools.parameters import basic
from galaxy.util import (
    bunch,
    XML,
)
from galaxy.util.unittest import TestCase

if TYPE_CHECKING:
    from galaxy.tools import Tool


class BaseParameterTestCase(TestCase, UsesApp):
    def setUp(self):
        self.setup_app()
        self.mock_tool = bunch.Bunch(
            app=self.app,
            tool_type="default",
            valid_input_states=model.Dataset.valid_input_states,
            profile=23.0,
        )

    def _parameter_for(self, **kwds):
        content = kwds["xml"]
        param_xml = XML(content)
        return basic.ToolParameter.build(cast("Tool", self.mock_tool), param_xml)
