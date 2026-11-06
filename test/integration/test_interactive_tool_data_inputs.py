"""Integration tests for ``GET /api/tools/data_inputs``."""

from typing import Any

from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver.integration_util import (
    CachedToolBoxIntegrationMixin,
    IntegrationTestCase,
)

TABULAR_INPUT_TOOL = "interactivetool_tabular_input"
ANY_INPUT_TOOL = "interactivetool_any_input"
REPEAT_INPUT_TOOL = "interactivetool_repeat_input"
CONDITIONAL_INPUT_TOOL = "interactivetool_conditional_input"
HIDDEN_INPUT_TOOL = "interactivetool_hidden_input"
LOGIN_INPUT_TOOL = "interactivetool_login_input"
SIMPLE_TOOL = "interactivetool_simple"
REGULAR_TOOL = "cat_data_and_sleep"


class TestInteractiveToolDataInputs(IntegrationTestCase):
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

    def test_interactive_tool_data_inputs(self):
        data_inputs = self._data_inputs(tool_type="interactive")
        assert data_inputs[TABULAR_INPUT_TOOL] == [
            {"name": "infile", "extensions": ["tabular"], "multiple": False, "type": "data", "collection_type": None}
        ]
        assert data_inputs[ANY_INPUT_TOOL] == [
            {"name": "infile", "extensions": ["data"], "multiple": False, "type": "data", "collection_type": None}
        ]
        assert data_inputs[REPEAT_INPUT_TOOL] == [
            {
                "name": "user_inputs_0|infile",
                "extensions": ["data"],
                "multiple": False,
                "type": "data",
                "collection_type": None,
            }
        ]
        assert data_inputs[CONDITIONAL_INPUT_TOOL] == [
            {"name": None, "extensions": ["tabular"], "multiple": False, "type": "data", "collection_type": None}
        ]
        # Tools without data inputs are left out.
        assert SIMPLE_TOOL not in data_inputs
        assert REGULAR_TOOL not in data_inputs

    def test_data_inputs_of_every_tool_type(self):
        data_inputs = self._data_inputs()
        assert TABULAR_INPUT_TOOL in data_inputs
        assert [data_input["name"] for data_input in data_inputs[REGULAR_TOOL]] == ["input1", "queries_0|input2"]

    def test_data_inputs_cover_only_listed_tools(self):
        response = self._get("tools", data={"in_panel": "False"})
        self._assert_status_code_is(response, 200)
        listed_tool_ids = {tool["id"] for tool in response.json()}
        assert set(self._data_inputs()) <= listed_tool_ids

    def test_data_inputs_apply_the_listing_filters(self):
        # The hidden tool is loaded, so its absence below comes from the filter.
        self._assert_status_code_is(self._get(f"tools/{HIDDEN_INPUT_TOOL}"), 200)
        tool_ids = set(self._data_inputs(tool_type="interactive"))
        assert LOGIN_INPUT_TOOL in tool_ids
        assert HIDDEN_INPUT_TOOL not in tool_ids
        with self._different_user(anon=True):
            anonymous_tool_ids = set(self._data_inputs(tool_type="interactive"))
        # The unrestricted tool guards against passing on an empty response.
        assert TABULAR_INPUT_TOOL in anonymous_tool_ids
        assert LOGIN_INPUT_TOOL not in anonymous_tool_ids
        assert HIDDEN_INPUT_TOOL not in anonymous_tool_ids

    def test_tool_listing_leaves_out_data_inputs(self):
        response = self._get("tools", data={"in_panel": "False"})
        self._assert_status_code_is(response, 200)
        tool = next(tool for tool in response.json() if tool["id"] == TABULAR_INPUT_TOOL)
        assert "data_inputs" not in tool

    def test_input_name_prefills_the_tool_form(self):
        dataset_id = self._new_dataset("1\t2\n", "tabular")
        # A newer tabular dataset would be the default, so the preselection must come from the input name.
        self._new_dataset("3\t4\n", "tabular")
        inputs = self._build_inputs(TABULAR_INPUT_TOOL, "infile", dataset_id)
        infile = next(i for i in inputs if i["name"] == "infile")
        assert infile["value"]["values"][0]["id"] == dataset_id

    def test_repeat_input_name_prefills_the_first_element(self):
        dataset_id = self._new_dataset("some text\n", "txt")
        self._new_dataset("more text\n", "txt")
        inputs = self._build_inputs(REPEAT_INPUT_TOOL, "user_inputs_0|infile", dataset_id)
        user_inputs = next(i for i in inputs if i["name"] == "user_inputs")
        infile = next(i for i in user_inputs["cache"][0] if i["name"] == "infile")
        assert infile["value"]["values"][0]["id"] == dataset_id

    def _data_inputs(self, tool_type: str | None = None) -> dict[str, list[dict[str, Any]]]:
        response = self._get("tools/data_inputs", data={"tool_type": tool_type} if tool_type else None)
        self._assert_status_code_is(response, 200)
        return response.json()

    def _new_dataset(self, content: str, file_type: str) -> str:
        hda = self.dataset_populator.new_dataset(
            self.dataset_history_id, content=content, file_type=file_type, wait=True
        )
        return hda["id"]

    def _build_inputs(self, tool_id: str, input_name: str, dataset_id: str) -> list[dict[str, Any]]:
        response = self._get(
            f"tools/{tool_id}/build", data={"history_id": self.dataset_history_id, input_name: dataset_id}
        )
        self._assert_status_code_is(response, 200)
        return response.json()["inputs"]


class TestInteractiveToolDataInputsCachedToolBox(CachedToolBoxIntegrationMixin, TestInteractiveToolDataInputs):
    pass
