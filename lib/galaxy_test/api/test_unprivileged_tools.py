# Test tools API.
from galaxy.schema.tools import UserToolSource
from galaxy_test.base.populators import (
    DatasetCollectionPopulator,
    DatasetPopulator,
)
from ._framework import ApiTestCase
from .test_tools import (
    TestsTools,
    TOOL_WITH_SHELL_COMMAND,
)


class TestUnprivilegedToolsApi(ApiTestCase, TestsTools):

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.dataset_collection_populator = DatasetCollectionPopulator(self.galaxy_interactor)

    def test_create_unprivileged(self):
        dynamic_tool = self.dataset_populator.create_unprivileged_tool(UserToolSource(**TOOL_WITH_SHELL_COMMAND))
        assert dynamic_tool["uuid"]

    def test_list_unprivileged(self):
        dynamic_tool = self.dataset_populator.create_unprivileged_tool(UserToolSource(**TOOL_WITH_SHELL_COMMAND))
        dynamic_tools = self.dataset_populator.get_unprivileged_tools()
        assert any(
            dynamic_tool["uuid"] == t["uuid"] for t in dynamic_tools
        ), f"Newly created dynamic tool {dynamic_tool['uuid']} not in dynamic tools list {dynamic_tools}"

    def test_show(self):
        dynamic_tool = self.dataset_populator.create_unprivileged_tool(UserToolSource(**TOOL_WITH_SHELL_COMMAND))
        show_response = self.dataset_populator.show_unprivileged_tool(dynamic_tool["uuid"])
        assert show_response["representation"]["name"]

    def test_run(self):
        dynamic_tool = self.dataset_populator.create_unprivileged_tool(UserToolSource(**TOOL_WITH_SHELL_COMMAND))
        # Run tool.
        with self.dataset_populator.test_history() as history_id:
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
        pass
