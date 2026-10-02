from typing import Any
from unittest.mock import patch
from uuid import uuid4

import pytest

from galaxy import (
    exceptions,
    model,
)
from galaxy.app_unittest_utils.toolbox_support import BaseToolBoxTestCase
from galaxy.managers.tools import DynamicToolManager
from galaxy.tool_util.unittest_utils import mock_trans
from galaxy.tool_util_models import UserToolSource
from galaxy.tool_util_models.dynamic_tool_models import DynamicUnprivilegedToolCreatePayload
from galaxy.tool_util_models.parameter_validators import ExpressionParameterValidatorModel
from galaxy.tools.parameters.validation import LengthValidator

REPRESENTATION: dict[str, Any] = {
    "class": "GalaxyUserTool",
    "id": "cat_user_tool",
    "name": "Cat user tool",
    "version": "1.0.0",
    "container": "busybox",
    "shell_command": "cat '$(inputs.input.path)' > output.txt",
    "inputs": [{"type": "data", "name": "input", "format": "txt"}],
    "outputs": [{"type": "data", "name": "output", "from_work_dir": "output.txt"}],
}


class TestUserDefinedToolLoading(BaseToolBoxTestCase):
    def setUp(self):
        super().setUp()
        assert self.toolbox
        self.app.config.enable_beta_tool_formats = True
        self.dynamic_tool_manager = DynamicToolManager(self.app)
        self.app.dynamic_tool_manager = self.dynamic_tool_manager

    def _executor(self) -> model.User:
        session = self.app.model.context
        user = model.User(email=f"u_{uuid4().hex}@example.com", password="pw")
        role = model.Role(name=f"udt_{uuid4().hex[:8]}", description="udt", type=model.Role.types.USER_TOOL_EXECUTE)
        session.add_all([user, role, model.UserRoleAssociation(user, role)])
        session.commit()
        return user

    def _create(self, user: model.User) -> model.DynamicTool:
        payload = DynamicUnprivilegedToolCreatePayload(representation=UserToolSource(**REPRESENTATION))
        return self.dynamic_tool_manager.create_unprivileged_tool(user, payload)

    def _job(self, user: model.User, dynamic_tool: model.DynamicTool) -> model.Job:
        job = model.Job()
        job.user = user
        job.tool_id = dynamic_tool.tool_id
        job.dynamic_tool = dynamic_tool
        return job

    def _stored(self, owner: model.User, representation: dict[str, Any]) -> model.DynamicTool:
        session = self.app.model.context
        dynamic_tool = model.DynamicTool(
            tool_format="GalaxyUserTool",
            tool_id=representation["id"],
            tool_version=representation["version"],
            uuid=uuid4(),
            value=representation,
            public=False,
            active=True,
        )
        session.add(dynamic_tool)
        session.flush()
        session.add(model.UserDynamicToolAssociation(user_id=owner.id, dynamic_tool_id=dynamic_tool.id))
        session.commit()
        return dynamic_tool

    def test_stored_tool_loads_without_fields_the_schema_no_longer_accepts(self):
        owner = self._executor()
        select = {"name": "sel", "type": "select", "options": [{"label": "A", "value": "a"}]}
        representation = {
            **REPRESENTATION,
            "command": "echo ${1 + 1}",
            "inputs": [*REPRESENTATION["inputs"], {**select, "dynamic_options": "x()"}],
        }
        dynamic_tool = self._stored(owner, representation)

        tool = self.toolbox.get_unprivileged_tool(owner, dynamic_tool.uuid)

        assert tool is not None
        assert not tool.command
        assert tool.shell_command == REPRESENTATION["shell_command"]
        assert tool.inputs["sel"].dynamic_options is None
        tool_dict = tool.to_dict(mock_trans())
        assert tool_dict["representation_status"] == "lifted"
        assert sorted(tool_dict["representation_errors"]) == ["command", "inputs.1.dynamic_options"]

    def test_current_tool_reports_no_dropped_fields(self):
        owner = self._executor()
        tool = self.toolbox.get_unprivileged_tool(owner, self._create(owner).uuid)
        assert tool is not None
        assert "representation_status" not in tool.to_dict(mock_trans())

    def test_stored_tool_with_expression_validator_loads_without_it(self):
        owner = self._executor()
        text = {
            "name": "text",
            "type": "text",
            "validators": [{"type": "expression", "expression": "value == 'x'"}, {"type": "length", "min": 1}],
        }
        dynamic_tool = self._stored(owner, {**REPRESENTATION, "inputs": [*REPRESENTATION["inputs"], text]})

        # The length validator evaluates an expression of its own; the stored one must never run.
        with patch.object(
            ExpressionParameterValidatorModel,
            "expression_validation",
            wraps=ExpressionParameterValidatorModel.expression_validation,
        ) as expression_validation:
            tool = self.toolbox.get_unprivileged_tool(owner, dynamic_tool.uuid)
            assert tool is not None
            text_parameter = tool.inputs["text"]
            assert [type(v) for v in text_parameter.validators] == [LengthValidator]
            text_parameter.validate("y")
        assert "value == 'x'" not in [call.args[0] for call in expression_validation.call_args_list]

        tool_dict = tool.to_dict(mock_trans())
        assert tool_dict["representation_status"] == "lifted"
        assert tool_dict["representation_errors"] == [
            "inputs.1.validators.0 (unsupported 'expression' validator on input 'text')"
        ]

    def test_stored_tool_that_cannot_be_lifted_is_refused(self):
        owner = self._executor()
        representation = {key: value for key, value in REPRESENTATION.items() if key != "shell_command"}
        dynamic_tool = self._stored(owner, representation)

        with pytest.raises(exceptions.ToolMissingException, match="shell_command") as exc_info:
            self.toolbox.get_unprivileged_tool(owner, dynamic_tool.uuid)
        assert "tool editor" in str(exc_info.value)
        assert self.toolbox.tool_for_job(self._job(owner, dynamic_tool), check_access=False) is None
