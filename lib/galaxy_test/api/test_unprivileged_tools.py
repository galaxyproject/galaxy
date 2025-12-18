# Test tools API.
from galaxy.tool_util_models import UserToolSource
from galaxy_test.base.populators import (
    DatasetCollectionPopulator,
    DatasetPopulator,
    TOOL_WITH_SHELL_COMMAND,
)
from ._framework import ApiTestCase
from .test_tools import TestsTools


class TestUnprivilegedToolsApi(ApiTestCase, TestsTools):

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.dataset_collection_populator = DatasetCollectionPopulator(self.galaxy_interactor)

    def test_create_unprivileged_requires_execute_role(self):
        dynamic_tool = self.dataset_populator.create_unprivileged_tool(
            UserToolSource(**TOOL_WITH_SHELL_COMMAND), assert_ok=False
        )
        assert dynamic_tool["err_msg"] == "User is not allowed to run unprivileged tools"

    def test_create_unprivileged(self):
        # Create a new dynamic tool.
        with self.dataset_populator.user_tool_execute_permissions():
            dynamic_tool = self.dataset_populator.create_unprivileged_tool(UserToolSource(**TOOL_WITH_SHELL_COMMAND))
            assert dynamic_tool["uuid"], "Dynamic tool UUID not found in response"
            assert dynamic_tool["representation"]["name"] == TOOL_WITH_SHELL_COMMAND["name"]

    def test_list_unprivileged(self):
        with self.dataset_populator.user_tool_execute_permissions():
            dynamic_tool = self.dataset_populator.create_unprivileged_tool(UserToolSource(**TOOL_WITH_SHELL_COMMAND))
            dynamic_tools = self.dataset_populator.get_unprivileged_tools()
        assert any(
            dynamic_tool["uuid"] == t["uuid"] for t in dynamic_tools
        ), f"Newly created dynamic tool {dynamic_tool['uuid']} not in dynamic tools list {dynamic_tools}"

    def test_show(self):
        with self.dataset_populator.user_tool_execute_permissions():
            dynamic_tool = self.dataset_populator.create_unprivileged_tool(UserToolSource(**TOOL_WITH_SHELL_COMMAND))
            show_response = self.dataset_populator.show_unprivileged_tool(dynamic_tool["uuid"])
        assert show_response["representation"]["name"]

    def test_build(self):
        with (
            self.dataset_populator.test_history() as history_id,
            self.dataset_populator.user_tool_execute_permissions(),
        ):
            response = self.dataset_populator.build_unprivileged_tool(
                UserToolSource(**TOOL_WITH_SHELL_COMMAND), history_id=history_id
            )
        assert response

    def test_build_runtime_model(self):
        with self.dataset_populator.user_tool_execute_permissions():
            response = self.dataset_populator.build_runtime_model_for_tool(UserToolSource(**TOOL_WITH_SHELL_COMMAND))
            assert response
            assert response["openapi"] == "3.1.0"
            assert response["components"]["schemas"]["inputs"]

    def test_run(self):
        with (
            self.dataset_populator.test_history() as history_id,
            self.dataset_populator.user_tool_execute_permissions(),
        ):
            # Create a new dynamic tool.
            # This is a shell command tool that will echo the input dataset.
            dynamic_tool = self.dataset_populator.create_unprivileged_tool(UserToolSource(**TOOL_WITH_SHELL_COMMAND))
            # Run tool.
            dataset = self.dataset_populator.new_dataset(history_id=history_id, content="abc")
            self._run(
                history_id=history_id,
                tool_uuid=dynamic_tool["uuid"],
                inputs={"input": {"src": "hda", "id": dataset["id"]}},
            )

            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            output_content = self.dataset_populator.get_history_dataset_content(history_id)
            assert output_content == "abc\n"

    def test_deactivate(self):
        with self.dataset_populator.user_tool_execute_permissions():
            # Create a new dynamic tool.
            dynamic_tool = self.dataset_populator.create_unprivileged_tool(UserToolSource(**TOOL_WITH_SHELL_COMMAND))
            # Deactivate the tool.
            self.dataset_populator.deactivate_unprivileged_tool(dynamic_tool["uuid"])
            # Check that the tool is deactivated.
            dynamic_tools = self.dataset_populator.get_unprivileged_tools()
            assert not any(
                dynamic_tool["uuid"] == t["uuid"] for t in dynamic_tools
            ), f"Dynamic tool {dynamic_tool['uuid']} still in dynamic tools list {dynamic_tools}"
