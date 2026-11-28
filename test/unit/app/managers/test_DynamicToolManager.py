from galaxy import (
    exceptions,
    model,
)
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
            representation={
                "class": "GalaxyTool",
                "name": "Test Tool",
                "version": tool_version,
                "shell_command": "echo 42",
            }
        )
        dynamic_tool = self.dynamic_tool_manager.create_tool(payload)
        assert dynamic_tool.active
        assert dynamic_tool.public
        assert dynamic_tool.tool_format == "GalaxyTool"
        assert dynamic_tool.tool_version == tool_version

    def test_create_tool_no_version(self):
        payload = DynamicToolCreatePayload(
            representation={"class": "GalaxyTool", "name": "Test Tool", "shell_command": "echo 42"}
        )
        with self.assertRaises(ValueError):
            self.dynamic_tool_manager.create_tool(payload)

    def test_create_tool_requires_beta_tool_formats(self):
        self.app.config.enable_beta_tool_formats = False
        payload = DynamicToolCreatePayload(
            representation={
                "class": "GalaxyTool",
                "name": "Test Tool",
                "version": "0.1",
                "shell_command": "echo 42",
            }
        )
        with self.assertRaises(exceptions.ConfigDoesNotAllowException):
            self.dynamic_tool_manager.create_tool(payload)

    def _user_without_execute_role(self):
        user = model.User(email="udt-no-role@galaxyproject.org", password="mockpass")
        session = self.app.model.session
        session.add(user)
        session.commit()
        return user

    def test_unprivileged_tools_require_execute_role_by_default(self):
        user = self._user_without_execute_role()
        with self.assertRaises(exceptions.InsufficientPermissionsException):
            self.dynamic_tool_manager.ensure_can_use_unprivileged_tool(user)

    def test_allow_user_defined_tools_for_all_users(self):
        self.app.config.allow_user_defined_tools_for_all_users = True
        user = self._user_without_execute_role()
        self.dynamic_tool_manager.ensure_can_use_unprivileged_tool(user)

    def test_allow_user_defined_tools_for_all_users_still_refuses_anonymous(self):
        self.app.config.allow_user_defined_tools_for_all_users = True
        with self.assertRaises(exceptions.InsufficientPermissionsException):
            self.dynamic_tool_manager.ensure_can_use_unprivileged_tool(None)
