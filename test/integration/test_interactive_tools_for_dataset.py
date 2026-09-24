"""Integration tests for ``GET /api/datasets/{dataset_id}/interactive_tools``."""

from typing import Any

from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver.integration_util import IntegrationTestCase

TABULAR_INPUT_TOOL = "interactivetool_tabular_input"
ANY_INPUT_TOOL = "interactivetool_any_input"
REPEAT_INPUT_TOOL = "interactivetool_repeat_input"


class TestInteractiveToolsForDataset(IntegrationTestCase):
    dataset_populator: DatasetPopulator
    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["interactivetools_enable"] = True

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.dataset_history_id = self.dataset_populator.new_history()

    def test_tabular_dataset(self):
        dataset_id = self._new_dataset("1\t2\n", "tabular")
        tools = self._interactive_tools(dataset_id)
        assert [(tool["id"], tool["match"], tool["input_name"]) for tool in tools] == [
            (TABULAR_INPUT_TOOL, "direct", "infile"),
            (ANY_INPUT_TOOL, "generic", "infile"),
            (REPEAT_INPUT_TOOL, "generic", "user_inputs_0|infile"),
        ]
        assert tools[0]["version"] == "0.1"
        assert tools[0]["icon"] is False
        # The build API must preselect the dataset by input name; a newer tabular dataset would be the default.
        self._new_dataset("3\t4\n", "tabular")
        inputs = self._build_inputs(TABULAR_INPUT_TOOL, "infile", dataset_id)
        infile = next(i for i in inputs if i["name"] == "infile")
        assert infile["value"]["values"][0]["id"] == dataset_id

    def test_dataset_matched_through_conversion(self):
        dataset_id = self._new_dataset(">seq1\nACGT\n", "fasta")
        tools = self._interactive_tools(dataset_id)
        assert [(tool["id"], tool["match"]) for tool in tools] == [
            (TABULAR_INPUT_TOOL, "converted"),
            (ANY_INPUT_TOOL, "generic"),
            (REPEAT_INPUT_TOOL, "generic"),
        ]

    def test_dataset_without_specific_tool(self):
        dataset_id = self._new_dataset("some text\n", "txt")
        tools = self._interactive_tools(dataset_id)
        assert [(tool["id"], tool["match"], tool["input_name"]) for tool in tools] == [
            (ANY_INPUT_TOOL, "generic", "infile"),
            (REPEAT_INPUT_TOOL, "generic", "user_inputs_0|infile"),
        ]
        # The build API creates the first repeat element from the input name and preselects the dataset in it.
        self._new_dataset("more text\n", "txt")
        inputs = self._build_inputs(REPEAT_INPUT_TOOL, "user_inputs_0|infile", dataset_id)
        user_inputs = next(i for i in inputs if i["name"] == "user_inputs")
        infile = next(i for i in user_inputs["cache"][0] if i["name"] == "infile")
        assert infile["value"]["values"][0]["id"] == dataset_id

    def test_inaccessible_dataset(self):
        dataset_id = self._new_dataset("1\t2\n", "tabular")
        self.dataset_populator.make_private(self.dataset_history_id, dataset_id)
        with self._different_user():
            response = self._get(f"datasets/{dataset_id}/interactive_tools")
        self._assert_status_code_is(response, 403)

    def _new_dataset(self, content: str, file_type: str) -> str:
        hda = self.dataset_populator.new_dataset(
            self.dataset_history_id, content=content, file_type=file_type, wait=True
        )
        return hda["id"]

    def _interactive_tools(self, dataset_id: str) -> list[dict[str, Any]]:
        response = self._get(f"datasets/{dataset_id}/interactive_tools")
        self._assert_status_code_is(response, 200)
        # Cached-toolbox runs also load the bundled interactive_tool_* tools from the sample tool_conf.
        return [tool for tool in response.json() if tool["id"].startswith("interactivetool_")]

    def _build_inputs(self, tool_id: str, input_name: str, dataset_id: str) -> list[dict[str, Any]]:
        response = self._get(
            f"tools/{tool_id}/build", data={"history_id": self.dataset_history_id, input_name: dataset_id}
        )
        self._assert_status_code_is(response, 200)
        return response.json()["inputs"]
