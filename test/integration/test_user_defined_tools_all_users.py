"""User-defined tools with ``allow_user_defined_tools_for_all_users`` enabled."""

from galaxy.tool_util_models import UserToolSource
from galaxy_test.base.api_mixins import TestsTools
from galaxy_test.base.populators import (
    DatasetPopulator,
    TOOL_WITH_SHELL_COMMAND,
)
from galaxy_test.driver import integration_util


class TestUserDefinedToolsForAllUsers(integration_util.IntegrationTestCase, TestsTools):
    dataset_populator: DatasetPopulator

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["allow_user_defined_tools_for_all_users"] = True

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def test_user_without_role_can_create_and_run(self):
        # A fresh user has never been granted the USER_TOOL_EXECUTE role.
        with self._different_user("udt-no-role@bx.psu.edu"):
            with self.dataset_populator.test_history() as history_id:
                dynamic_tool = self.dataset_populator.create_unprivileged_tool(
                    UserToolSource(**TOOL_WITH_SHELL_COMMAND)
                )
                dataset = self.dataset_populator.new_dataset(history_id=history_id, content="abc")
                self._run(
                    history_id=history_id,
                    tool_uuid=dynamic_tool["uuid"],
                    inputs={"input": {"src": "hda", "id": dataset["id"]}},
                    wait_for_job=True,
                    assert_ok=True,
                )
                output_content = self.dataset_populator.get_history_dataset_content(history_id)
                assert output_content == "abc\n"
                listed = self.dataset_populator.get_unprivileged_tools()
                assert dynamic_tool["uuid"] in [t["uuid"] for t in listed]

    def test_anonymous_user_still_refused(self):
        # Every unprivileged-tools endpoint and the tool_uuid lookup in /api/tools need a user
        # before they reach the manager's gate, so this checks the HTTP surface; the gate's own
        # anonymous refusal is covered in test_DynamicToolManager.
        with self.dataset_populator.test_history() as history_id:
            dynamic_tool = self.dataset_populator.create_unprivileged_tool(UserToolSource(**TOOL_WITH_SHELL_COMMAND))
            dataset = self.dataset_populator.new_dataset(history_id=history_id, content="abc")
            with self._different_user(anon=True):
                response = self.dataset_populator.create_unprivileged_tool_raw(
                    UserToolSource(**TOOL_WITH_SHELL_COMMAND)
                )
                assert response.status_code == 403, response.text
                assert response.json()["err_msg"] == "Action requires user authentication."
                response = self._run(
                    history_id=history_id,
                    tool_uuid=dynamic_tool["uuid"],
                    inputs={"input": {"src": "hda", "id": dataset["id"]}},
                )
                assert response.status_code == 404, response.text
