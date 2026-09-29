from typing import Any

import pytest

from galaxy import model
from galaxy.tool_util_models.tool_outputs import MAX_USER_TOOL_LABEL_LENGTH
from galaxy.tools.expressions.labels import render_user_tool_label
from galaxy.tools.parameters.workflow_utils import (
    ConnectedValue,
    RuntimeValue,
)


def _hda(name: str, extension: str = "txt") -> model.HistoryDatasetAssociation:
    return model.HistoryDatasetAssociation(name=name, extension=extension, create_dataset=True, flush=False)


def _render(label: str, state: dict[str, Any], on_string: str = "data 1") -> str:
    return render_user_tool_label(label, state.keys(), state, on_string)


STATE: dict[str, Any] = {
    "input": _hda("reads.fastq", "fastqsanger"),
    "n": 3,
    "x": 1.5,
    "opt": None,
    "cond": {"select": "a", "__current_case__": 0, "value": "nested"},
}
KEPT_AS_WRITTEN = (
    "$(inputs.missing) $(inputs.input) $(inputs.input.path) $(inputs.n.x) $(inputs.cond.__current_case__) "
    "${1 + 1} $(1 + 1) $(inputs['n'])"
)


@pytest.mark.parametrize(
    "label,expected",
    [
        ("from $(inputs.input.name) as $(inputs.input.format)", "from reads.fastq as fastqsanger"),
        ("$(inputs.input.element_identifier)", "reads.fastq"),
        ("n=$(inputs.n) x=$(inputs.x) on $(runtime.on_string)", "n=3 x=1.5 on data 1"),
        ("$(inputs.cond.value)", "nested"),
        ("[$(inputs.opt)] [$(inputs.opt.name)]", "[] []"),
        (KEPT_AS_WRITTEN, KEPT_AS_WRITTEN),
    ],
)
def test_references_filled_in(label, expected):
    assert _render(label, STATE) == expected


def test_only_declared_inputs_filled_in():
    assert render_user_tool_label("$(inputs.n)", ["input"], STATE, None) == "$(inputs.n)"


def test_on_string_without_value_kept_as_written():
    assert render_user_tool_label("$(runtime.on_string)", [], {}, None) == "$(runtime.on_string)"


def test_label_cut_to_limit():
    assert _render("$(inputs.v)", {"v": "x" * 300}) == "x" * MAX_USER_TOOL_LABEL_LENGTH
    # Only a tool stored before the length limit has a longer label; it is cut before filling in.
    stored = "$(inputs.n)" + "x" * 300
    assert _render(stored, STATE) == "3" + stored[len("$(inputs.n)") : MAX_USER_TOOL_LABEL_LENGTH]


def test_collections():
    collection = model.DatasetCollection(collection_type="list:paired")
    element = model.DatasetCollectionElement(
        collection=collection, element=model.DatasetCollection(collection_type="paired"), element_identifier="sample1"
    )
    hdca = model.HistoryDatasetCollectionAssociation(collection=collection, name="samples")
    label = "$(inputs.c.name) $(inputs.c.element_identifier) $(inputs.e.name) $(inputs.c.format)"
    assert _render(label, {"c": hdca, "e": element}) == "samples samples sample1 $(inputs.c.format)"


def test_workflow_editor_runtime_values_kept_as_written():
    state = {"input": ConnectedValue(), "n": RuntimeValue(), "cond": {"value": {"__class__": "ConnectedValue"}}}
    label = "$(inputs.input.name) $(inputs.n) $(inputs.cond.value)"
    assert _render(label, state) == label
