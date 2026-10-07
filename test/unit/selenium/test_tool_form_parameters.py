"""Flattening a tool's build model into the parameter paths tool_form_fill takes."""

from typing import Any

from galaxy.selenium.tool_form import (
    repeat_instance_counts,
    tool_form_parameters_from_build,
    ToolFormParameter,
)

HDA = {"id": "e89067bb68bee7a0", "hid": 1, "name": "Pasted Dataset 1", "src": "hda"}
DATA_OPTIONS = {"dce": [], "ldda": [], "hda": [HDA], "hdca": []}


def _data(name, label):
    return {
        "name": name,
        "type": "data",
        "label": label,
        "value": {"values": [{"id": HDA["id"], "src": "hda"}]},
        "optional": False,
        "options": DATA_OPTIONS,
    }


def test_data_and_repeat_paths():
    inputs = [
        _data("input1", "Concatenate Dataset"),
        {
            "name": "queries",
            "type": "repeat",
            "title": "Dataset",
            "min": 0,
            "max": None,
            "inputs": [_data("input2", "Select")],
            "cache": [],
        },
    ]
    assert tool_form_parameters_from_build(inputs) == [
        ToolFormParameter(
            "input1", "Concatenate Dataset", "data", "1: Pasted Dataset 1", [("1: Pasted Dataset 1", "1")]
        ),
        ToolFormParameter("queries", "Dataset", "repeat", 0, []),
        ToolFormParameter("queries_0|input2", "Select", "data", "1: Pasted Dataset 1", [("1: Pasted Dataset 1", "1")]),
    ]


def test_conditional_lists_every_case_with_its_condition():
    inputs = [
        {
            "name": "conditional_parameter",
            "type": "conditional",
            "test_param": {
                "name": "test_parameter",
                "type": "select",
                "label": "",
                "value": "a",
                "options": [["A", "a", False], ["B", "b", False]],
            },
            "cases": [
                {"value": "a", "inputs": [{"name": "integer_parameter", "type": "integer", "label": "", "value": "1"}]},
                {
                    "value": "b",
                    "inputs": [{"name": "boolean_parameter", "type": "boolean", "label": "Flag", "value": False}],
                },
            ],
        }
    ]
    assert tool_form_parameters_from_build(inputs) == [
        ToolFormParameter(
            "conditional_parameter|test_parameter", "test_parameter", "select", "a", [("A", "a"), ("B", "b")]
        ),
        ToolFormParameter(
            "conditional_parameter|integer_parameter",
            "integer_parameter",
            "integer",
            "1",
            [],
            "conditional_parameter|test_parameter=a",
        ),
        ToolFormParameter(
            "conditional_parameter|boolean_parameter",
            "Flag",
            "boolean",
            False,
            [],
            "conditional_parameter|test_parameter=b",
        ),
    ]


def test_section_and_repeat_instances_use_form_prefixes():
    inputs: list[dict[str, Any]] = [
        {
            "name": "parameter",
            "type": "section",
            "title": "Options",
            "inputs": [{"name": "flag", "type": "boolean", "label": "", "value": True}],
        },
        {
            "name": "the_repeat",
            "type": "repeat",
            "title": "Repeat",
            "inputs": [{"name": "texttest", "type": "text", "label": "", "value": ""}],
            "cache": [
                [{"name": "texttest", "type": "text", "label": "", "value": "one"}],
                [{"name": "texttest", "type": "text", "label": "", "value": "two"}],
            ],
        },
    ]
    assert [(p.path, p.value) for p in tool_form_parameters_from_build(inputs)] == [
        ("parameter|flag", True),
        ("the_repeat", 2),
        ("the_repeat_0|texttest", "one"),
        ("the_repeat_1|texttest", "two"),
    ]


def test_drill_down_options_flatten_nested_options():
    inputs = [
        {
            "name": "parameter",
            "type": "drill_down",
            "label": "",
            "value": "ab",
            "options": [
                {
                    "name": "A",
                    "value": "a",
                    "options": [{"name": "AB", "value": "ab", "options": []}],
                },
                {"name": "B", "value": "b", "options": []},
            ],
        }
    ]
    assert tool_form_parameters_from_build(inputs) == [
        ToolFormParameter("parameter", "parameter", "drill_down", "ab", [("A", "a"), ("AB", "ab"), ("B", "b")]),
    ]


def test_data_lists_pinned_selection_before_page_options():
    pinned = {"id": "f2db41e1fa331b3e", "hid": 7, "name": "Rerun Input", "src": "hda", "keep": True}
    inputs = [
        {
            "name": "input1",
            "type": "data",
            "label": "Input",
            "value": {"values": [{"id": pinned["id"], "src": "hda"}]},
            "options": DATA_OPTIONS,
            "pinned": {"dce": [], "ldda": [], "hda": [pinned], "hdca": []},
        }
    ]
    assert tool_form_parameters_from_build(inputs) == [
        ToolFormParameter(
            "input1",
            "Input",
            "data",
            "7: Rerun Input",
            [("7: Rerun Input", "7"), ("1: Pasted Dataset 1", "1")],
        ),
    ]


def test_data_value_label_matches_source_not_just_id():
    hdca = {"id": HDA["id"], "hid": 2, "name": "A Collection", "src": "hdca"}
    inputs = [
        {
            "name": "input1",
            "type": "data",
            "label": "Input",
            "value": {"values": [{"id": HDA["id"], "src": "hda"}]},
            "options": {"dce": [], "ldda": [], "hda": [HDA], "hdca": [hdca]},
        }
    ]
    assert tool_form_parameters_from_build(inputs)[0].value == "1: Pasted Dataset 1"


def test_data_value_from_pinned_collection_element_uses_its_name():
    dce = {"id": "a799d38679e985db", "hid": -1, "name": "forward", "src": "dce", "tags": []}
    inputs = [
        {
            "name": "input1",
            "type": "data",
            "label": "Input",
            "value": {"values": [{"id": dce["id"], "src": "dce"}]},
            "options": DATA_OPTIONS,
            "pinned": {"dce": [dce], "ldda": [], "hda": [], "hdca": []},
        }
    ]
    assert tool_form_parameters_from_build(inputs) == [
        ToolFormParameter("input1", "Input", "data", "forward", [("1: Pasted Dataset 1", "1")]),
    ]


def test_repeat_instance_counts_take_the_highest_index_per_repeat():
    paths = ["queries_1|input2", "queries_0|input2", "input1", "cond|outer_0|x", "a_b_3|c"]
    assert repeat_instance_counts(paths) == {"queries": 2, "cond|outer": 1, "a_b": 4}
