from typing import Any

from galaxy.tool_util_models import UserToolSource
from galaxy_test.base.populators import (
    DatasetCollectionPopulator,
    DatasetPopulator,
    TOOL_WITH_SHELL_COMMAND,
)
from ._framework import ApiTestCase

LABELS = {
    "history_name": "from $(inputs.input.name)",
    "on_string": "$(runtime.on_string) filtered",
    "scalar": "n=$(inputs.n)",
    "conditional": "suffix $(inputs.cond.suffix)",
    "optional": "[$(inputs.extra.name)]",
}
LABEL_TOOL: dict[str, Any] = {
    **TOOL_WITH_SHELL_COMMAND,
    "shell_command": "for f in " + " ".join(LABELS) + "; do cat '$(inputs.input.path)' > $f.txt; done",
    "inputs": [
        {"type": "data", "name": "input", "format": "txt"},
        {"type": "data", "name": "extra", "format": "txt", "optional": True},
        {"type": "integer", "name": "n", "value": 7},
        {
            "type": "conditional",
            "name": "cond",
            "test_parameter": {"type": "boolean", "name": "test_parameter"},
            "whens": [
                {"discriminator": True, "parameters": []},
                {"discriminator": False, "parameters": [{"type": "text", "name": "suffix", "value": "trimmed"}]},
            ],
        },
    ],
    "outputs": [
        {"type": "data", "name": name, "from_work_dir": f"{name}.txt", "label": label} for name, label in LABELS.items()
    ],
}


def _user_tool(**overrides: Any) -> UserToolSource:
    return UserToolSource(**{**TOOL_WITH_SHELL_COMMAND, **overrides})


def _data_output(label: str) -> dict[str, Any]:
    return {"type": "data", "name": "output", "from_work_dir": "output.fastq", "label": label}


def _batch(hdca: dict[str, Any]) -> dict[str, Any]:
    return {"batch": True, "values": [{"src": "hdca", "id": hdca["id"]}]}


class TestUnprivilegedToolsLabelsApi(ApiTestCase):

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.dataset_collection_populator = DatasetCollectionPopulator(self.galaxy_interactor)

    def _run(self, history_id: str, representation: UserToolSource, inputs: dict[str, Any]) -> dict[str, Any]:
        dynamic_tool = self.dataset_populator.create_unprivileged_tool(representation)
        response = self.dataset_populator.run_tool_raw(
            tool_id=None, tool_uuid=dynamic_tool["uuid"], inputs=inputs, history_id=history_id
        )
        self._assert_status_code_is(response, 200)
        return response.json()

    def _reads(self, history_id: str) -> dict[str, Any]:
        return self.dataset_populator.new_dataset(history_id=history_id, content="abc", name="reads.txt")

    def _list(self, history_id: str, contents: list) -> dict[str, Any]:
        return self.dataset_collection_populator.create_list_in_history(
            history_id, contents=contents, wait=True
        ).json()["outputs"][0]

    def test_data_output_labels_resolve_parameter_references(self):
        with (
            self.dataset_populator.test_history() as history_id,
            self.dataset_populator.user_tool_execute_permissions(),
        ):
            dataset = self._reads(history_id)
            run = self._run(history_id, UserToolSource(**LABEL_TOOL), {"input": {"src": "hda", "id": dataset["id"]}})
            display = self._get(f"jobs/{run['jobs'][0]['id']}/parameters_display").json()
        expected = {
            "history_name": "from reads.txt",
            "on_string": f"dataset {dataset['hid']} filtered",
            "scalar": "n=7",
            "conditional": "suffix trimmed",
            "optional": "[]",
        }
        assert {output["output_name"]: output["name"] for output in run["outputs"]} == expected
        # The job parameters page has no input description to fill in on_string with.
        expected["on_string"] = LABELS["on_string"]
        assert {name: outputs[0]["label"] for name, outputs in display["outputs"].items()} == expected

    def test_collection_output_label_resolves_parameter_references(self):
        output = {
            "type": "collection",
            "name": "outs",
            "collection_type": "list",
            "discover_datasets": [{"pattern": "*.txt"}],
            "label": "$(inputs.input.name) split",
        }
        representation = _user_tool(shell_command="cp '$(inputs.input.path)' a.txt", outputs=[output])
        with (
            self.dataset_populator.test_history() as history_id,
            self.dataset_populator.user_tool_execute_permissions(),
        ):
            run = self._run(history_id, representation, {"input": {"src": "hda", "id": self._reads(history_id)["id"]}})
        assert run["output_collections"][0]["name"] == "reads.txt split"

    def test_mapped_over_labels(self):
        representation = _user_tool(
            inputs=[
                {"type": "data", "name": "input", "format": "txt"},
                {"type": "integer", "name": "n", "value": 7},
            ],
            outputs=[_data_output("n=$(inputs.n) $(inputs.input.element_identifier)")],
        )
        with (
            self.dataset_populator.test_history() as history_id,
            self.dataset_populator.user_tool_execute_permissions(),
        ):
            hdca = self._list(history_id, [("sample1", "a"), ("sample2", "b")])
            for element in self._get(f"dataset_collections/{hdca['id']}").json()["elements"]:
                self.dataset_populator.update_dataset(element["object"]["id"], {"name": "renamed"})
            run = self._run(history_id, representation, {"input": _batch(hdca)})
        assert run["implicit_collections"][0]["name"] == f"n=7 {hdca['name']}"
        assert sorted(output["name"] for output in run["outputs"]) == ["n=7 sample1", "n=7 sample2"]

    def test_mapped_over_nested_input_label_uses_collection(self):
        representation = _user_tool(
            shell_command="cat '$(inputs.cond.input.path)' > output.fastq",
            inputs=[
                {
                    "type": "conditional",
                    "name": "cond",
                    "test_parameter": {"type": "boolean", "name": "test_parameter"},
                    "whens": [
                        {"discriminator": True, "parameters": [{"type": "data", "name": "input", "format": "txt"}]},
                        {"discriminator": False, "parameters": []},
                    ],
                },
            ],
            outputs=[_data_output("from $(inputs.cond.input.name)")],
        )
        with (
            self.dataset_populator.test_history() as history_id,
            self.dataset_populator.user_tool_execute_permissions(),
        ):
            hdca = self._list(history_id, ["a", "b"])
            run = self._run(history_id, representation, {"cond|test_parameter": True, "cond|input": _batch(hdca)})
        assert run["implicit_collections"][0]["name"] == f"from {hdca['name']}"

    def test_workflow_editor_output_labels(self):
        with self.dataset_populator.user_tool_execute_permissions():
            dynamic_tool = self.dataset_populator.create_unprivileged_tool(UserToolSource(**LABEL_TOOL))
            response = self._post(
                "workflows/build_module",
                data={"type": "tool", "tool_uuid": dynamic_tool["uuid"], "inputs": {}},
                json=True,
            )
        self._assert_status_code_is(response, 200)
        labels = {output["name"]: output["label"] for output in response.json()["outputs"]}
        assert labels == {
            # The data inputs are not connected in the editor, so references to them stay literal.
            "history_name": LABELS["history_name"],
            "on_string": "input dataset(s) filtered",
            "scalar": "n=7",
            "conditional": "suffix trimmed",
            "optional": LABELS["optional"],
        }
