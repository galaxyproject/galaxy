from galaxy.tool_util.parameters import input_models_for_tool_source
from galaxy.tool_util.parameters.data_inputs import (
    data_inputs_for_parameters,
    ToolDataInput,
)
from galaxy.tool_util.parser.factory import get_tool_source

NESTED_INPUTS_TOOL = """<tool id="nested_inputs" name="Nested inputs" version="1.0">
    <command>true</command>
    <inputs>
        <param name="top" type="data" format="tabular,csv" multiple="true" />
        <section name="sec" title="Section">
            <param name="in_section" type="data" format="tabular" />
        </section>
        <conditional name="cond">
            <param name="mode" type="select">
                <option value="a">A</option>
                <option value="b">B</option>
            </param>
            <when value="a">
                <param name="in_default_case" type="data" format="tabular" />
            </when>
            <when value="b">
                <param name="in_other_case" type="data" format="tabular" />
                <repeat name="other_rep" title="Repeat in other case">
                    <param name="in_other_case_repeat" type="data" format="tabular" />
                </repeat>
            </when>
        </conditional>
        <repeat name="rep" title="Repeat">
            <param name="in_repeat" type="data" format="tabular" />
        </repeat>
        <param name="collection" type="data_collection" collection_type="list" />
    </inputs>
    <outputs />
</tool>
"""

SELECTED_CASE_TOOL = """<tool id="selected_case" name="Selected case" version="1.0">
    <command>true</command>
    <inputs>
        <conditional name="cond">
            <param name="mode" type="select">
                <option value="a">A</option>
                <option value="b" selected="true">B</option>
            </param>
            <when value="a">
                <param name="in_a" type="data" format="tabular" />
            </when>
            <when value="b">
                <param name="in_b" type="data" />
            </when>
        </conditional>
    </inputs>
    <outputs />
</tool>
"""


def _data_inputs(raw_tool_source: str) -> list[ToolDataInput]:
    tool_source = get_tool_source(tool_source_class="XmlToolSource", raw_tool_source=raw_tool_source)
    return data_inputs_for_parameters(input_models_for_tool_source(tool_source).parameters)


def test_data_inputs_names_follow_the_input_tree():
    assert [(data_input.name, data_input.extensions) for data_input in _data_inputs(NESTED_INPUTS_TOOL)] == [
        ("top", ["tabular", "csv"]),
        ("sec|in_section", ["tabular"]),
        ("cond|in_default_case", ["tabular"]),
        (None, ["tabular"]),
        (None, ["tabular"]),
        ("rep_0|in_repeat", ["tabular"]),
    ]


def test_data_inputs_carry_multiple():
    assert [data_input.multiple for data_input in _data_inputs(NESTED_INPUTS_TOOL)] == [
        True,
        False,
        False,
        False,
        False,
        False,
    ]


def test_data_inputs_use_the_selected_case_as_default():
    assert [(data_input.name, data_input.extensions) for data_input in _data_inputs(SELECTED_CASE_TOOL)] == [
        (None, ["tabular"]),
        ("cond|in_b", ["data"]),
    ]


def test_data_inputs_empty_without_data_params():
    assert data_inputs_for_parameters([]) == []
