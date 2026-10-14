"""Integration tests for loading stored user-defined tools."""

from typing import Any
from uuid import uuid4

from galaxy.model import (
    DynamicTool,
    UserDynamicToolAssociation,
)
from galaxy_test.api.test_tools import TestsTools
from galaxy_test.base.populators import (
    DatasetPopulator,
    TOOL_WITH_SHELL_COMMAND,
)
from galaxy_test.driver import integration_util


class TestUserDefinedToolLoading(integration_util.IntegrationTestCase, TestsTools):
    dataset_populator: DatasetPopulator

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["enable_beta_tool_formats"] = True

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def _store_tool_row(self, representation: dict[str, Any]) -> str:
        """Store a row the way an older Galaxy may have, bypassing today's validation."""
        user_id = self._app.security.decode_id(self.dataset_populator.user_id())
        session = self._app.model.session
        dynamic_tool = DynamicTool(
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
        session.add(UserDynamicToolAssociation(user_id=user_id, dynamic_tool_id=dynamic_tool.id))
        session.commit()
        return str(dynamic_tool.uuid)

    def test_stored_tool_loads_without_fields_the_schema_no_longer_accepts(self):
        with (
            self.dataset_populator.test_history() as history_id,
            self.dataset_populator.user_tool_execute_permissions(),
        ):
            uuid = self._store_tool_row({**TOOL_WITH_SHELL_COMMAND, "command": "echo ${1 + 1} > output.fastq"})
            dataset = self.dataset_populator.new_dataset(history_id=history_id, content="abc", wait=True)

            build_response = self._get(f"tools/{uuid}/build", data={"tool_uuid": uuid, "history_id": history_id})
            assert build_response.status_code == 200, build_response.text
            tool_form = build_response.json()
            assert tool_form["representation_status"] == "lifted"
            assert tool_form["representation_errors"] == ["command"]

            run_response = self._run(
                history_id=history_id, tool_uuid=uuid, inputs={"input": {"src": "hda", "id": dataset["id"]}}
            )
            assert run_response.status_code == 200, run_response.text
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            assert self.dataset_populator.get_history_dataset_content(history_id) == "abc\n"

    def test_stored_tool_loads_without_its_expression_validator(self):
        text = {"name": "text", "type": "text", "validators": [{"type": "expression", "expression": "value == 'x'"}]}
        representation = {**TOOL_WITH_SHELL_COMMAND, "inputs": [*TOOL_WITH_SHELL_COMMAND["inputs"], text]}
        expected_errors = ["inputs.1.validators.0 (unsupported 'expression' validator on input 'text')"]
        with (
            self.dataset_populator.test_history() as history_id,
            self.dataset_populator.user_tool_execute_permissions(),
        ):
            uuid = self._store_tool_row(representation)
            dataset = self.dataset_populator.new_dataset(history_id=history_id, content="abc", wait=True)

            show_response = self._get(f"unprivileged_tools/{uuid}")
            assert show_response.status_code == 200, show_response.text
            assert show_response.json()["representation_status"] == "lifted"
            assert show_response.json()["representation_errors"] == expected_errors

            build_response = self._get(f"tools/{uuid}/build", data={"tool_uuid": uuid, "history_id": history_id})
            assert build_response.status_code == 200, build_response.text
            tool_form = build_response.json()
            assert tool_form["representation_status"] == "lifted"
            assert tool_form["representation_errors"] == expected_errors
            assert "Edit the tool and save it again" in tool_form["message"]

            # "y" fails the stored validator, so the job only runs if the validator is gone.
            run_response = self._run(
                history_id=history_id,
                tool_uuid=uuid,
                inputs={"input": {"src": "hda", "id": dataset["id"]}, "text": "y"},
            )
            assert run_response.status_code == 200, run_response.text
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)

    def test_stored_tool_that_cannot_be_lifted_is_refused(self):
        representation = {key: value for key, value in TOOL_WITH_SHELL_COMMAND.items() if key != "shell_command"}
        with (
            self.dataset_populator.test_history() as history_id,
            self.dataset_populator.user_tool_execute_permissions(),
        ):
            uuid = self._store_tool_row(representation)
            dataset = self.dataset_populator.new_dataset(history_id=history_id, content="abc", wait=True)

            build_response = self._get(f"tools/{uuid}/build", data={"tool_uuid": uuid, "history_id": history_id})
            assert build_response.status_code == 400, build_response.text
            err_msg = build_response.json()["err_msg"]
            assert "shell_command" in err_msg
            assert "tool editor" in err_msg

            run_response = self._run(
                history_id=history_id, tool_uuid=uuid, inputs={"input": {"src": "hda", "id": dataset["id"]}}
            )
            assert run_response.status_code == 400, run_response.text
            assert "shell_command" in run_response.json()["err_msg"]
