from galaxy.app_unittest_utils.toolbox_support import BaseToolBoxTestCase
from galaxy.managers.tools import DynamicToolManager
from galaxy.tool_util_models.dynamic_tool_models import DynamicToolCreatePayload


class TestDynamicToolManager(BaseToolBoxTestCase):
    def setUp(self):
        super().setUp()
        # Initialize toolbox
        assert self.toolbox
        self.dynamic_tool_manager = DynamicToolManager(self.app)
        self.app.config.enable_beta_tool_formats = True

    def test_create_tool(self):
        tool_version = "0.1"
        payload = DynamicToolCreatePayload(
            representation={"class": "GalaxyTool", "version": tool_version, "command": "echo 42"}
        )
        dynamic_tool = self.dynamic_tool_manager.create_tool(payload)
        assert dynamic_tool.active
        assert dynamic_tool.public
        assert dynamic_tool.tool_format == "GalaxyTool"
        assert dynamic_tool.tool_version == tool_version

    def test_create_tool_no_version(self):
        payload = DynamicToolCreatePayload(representation={"class": "GalaxyTool", "command": "echo 42"})
        with self.assertRaises(ValueError):
            self.dynamic_tool_manager.create_tool(payload)
