"""Test tool execution pieces.

Longer term ideally we would separate all the tool tests in test_tools.py that
describe tool execution into this file and make sure we have parallel or matching
tests for both the legacy tool execution API and the tool request API. We would then
keep things like testing other tool APIs in ./test_tools.py (index, search, tool test
files, etc..).
"""

from galaxy_test.base.decorators import requires_tool_id
from galaxy_test.base.populators import (
    DescribeToolInputs,
    RequiredTool,
    TargetHistory,
)


@requires_tool_id("multi_data_param")
def test_multidata_param(target_history: TargetHistory, required_tool: RequiredTool):
    hda1 = target_history.with_dataset("1\t2\t3").src_dict
    hda2 = target_history.with_dataset("4\t5\t6").src_dict
    execution = required_tool.execute.with_inputs(
        {
            "f1": {"batch": False, "values": [hda1, hda2]},
            "f2": {"batch": False, "values": [hda2, hda1]},
        }
    )
    execution.assert_has_job(0).with_output("out1").with_contents("1\t2\t3\n4\t5\t6\n")
    execution.assert_has_job(0).with_output("out2").with_contents("4\t5\t6\n1\t2\t3\n")


@requires_tool_id("expression_forty_two")
def test_galaxy_expression_tool_simplest(required_tool: RequiredTool):
    required_tool.execute.assert_has_single_job.with_single_output.with_contents("42")


@requires_tool_id("expression_parse_int")
def test_galaxy_expression_tool_simple(required_tool: RequiredTool):
    execution = required_tool.execute.with_inputs({"input1": "7"})
    execution.assert_has_single_job.with_single_output.with_contents("7")


@requires_tool_id("expression_log_line_count")
def test_galaxy_expression_metadata(target_history: TargetHistory, required_tool: RequiredTool):
    hda1 = target_history.with_dataset("1\n2\n3\n4\n5\n6\n7\n8\n9\n10\n11\n12\n13\n14").src_dict
    execution = required_tool.execute.with_inputs({"input1": hda1})
    execution.assert_has_single_job.with_single_output.with_contents("3")


@requires_tool_id("multi_select")
def test_multi_select_as_list(required_tool: RequiredTool):
    execution = required_tool.execute.with_inputs({"select_ex": ["--ex1", "ex2"]})
    execution.assert_has_single_job.with_output("output").with_contents("--ex1,ex2")


@requires_tool_id("multi_select")
def test_multi_select_optional(required_tool: RequiredTool):
    execution = required_tool.execute.with_inputs(
        {
            "select_ex": ["--ex1"],
            "select_optional": None,
        }
    )
    job = execution.assert_has_single_job
    job.assert_has_output("output").with_contents("--ex1")
    job.assert_has_output("output2").with_contents_stripped("None")


@requires_tool_id("identifier_single")
def test_identifier_outside_map(target_history: TargetHistory, required_tool: RequiredTool):
    hda = target_history.with_dataset("123", named="Plain HDA")
    execute = required_tool.execute.with_inputs({"input1": hda.src_dict})
    execute.assert_has_single_job.assert_has_single_output.with_contents_stripped("Plain HDA")


@requires_tool_id("identifier_multiple")
def test_identifier_in_multiple_reduce(target_history: TargetHistory, required_tool: RequiredTool):
    hdca = target_history.with_pair()
    execute = required_tool.execute.with_inputs({"input1": hdca.src_dict})
    execute.assert_has_single_job.assert_has_single_output.with_contents_stripped("forward\nreverse")


@requires_tool_id("identifier_in_conditional")
def test_identifier_map_over_multiple_input_in_conditional(
    target_history: TargetHistory, required_tool: RequiredTool, tool_input_format: DescribeToolInputs
):
    hdca = target_history.with_pair()
    inputs = tool_input_format.when.flat({
        "outer_cond|input1": hdca.src_dict,
    }).when.nested(
        {
            "outer_cond": {
                "multi_input": True,
                "input1": hdca.src_dict,
            },
        }
    )
    execute = required_tool.execute.with_inputs(inputs)
    execute.assert_has_single_job.assert_has_single_output.with_contents_stripped("forward\nreverse")


@requires_tool_id("identifier_multiple_in_repeat")
def test_identifier_multiple_reduce_in_repeat_new_payload_form(
    target_history: TargetHistory, required_tool: RequiredTool
):
    hdca = target_history.with_pair()
    execute = required_tool.execute.with_nested_inputs(
        {
            "the_repeat": [{"the_data": {"input1": hdca.src_dict}}],
        }
    )
    execute.assert_has_single_job.assert_has_single_output.with_contents_stripped("forward\nreverse")


@requires_tool_id("output_action_change_format")
def test_map_over_with_output_format_actions(target_history: TargetHistory, required_tool: RequiredTool):
    hdca = target_history.with_pair()
    for use_action in ["do", "dont"]:
        execute = required_tool.execute.with_inputs(
            {
                "input_cond|dispatch": use_action,
                "input_cond|input": {"batch": True, "values": [hdca.src_dict]},
            }
        )
        execute.assert_has_n_jobs(2).assert_creates_n_implicit_collections(1)
        expected_extension = "txt" if (use_action == "do") else "data"
        execute.assert_has_job(0).with_single_output.with_file_ext(expected_extension)
        execute.assert_has_job(1).with_single_output.with_file_ext(expected_extension)


@requires_tool_id("output_action_change_format_paired")
def test_map_over_with_nested_paired_output_format_actions(target_history: TargetHistory, required_tool: RequiredTool):
    hdca = target_history.with_example_list_of_pairs()
    execute = required_tool.execute.with_inputs(
        {"input": {"batch": True, "values": [dict(map_over_type="paired", **hdca.src_dict)]}}
    )
    execute.assert_has_n_jobs(2).assert_creates_n_implicit_collections(1)
    execute.assert_has_job(0).with_single_output.with_file_ext("txt")
    execute.assert_has_job(1).with_single_output.with_file_ext("txt")


@requires_tool_id("identifier_collection")
def test_identifier_with_data_collection(target_history: TargetHistory, required_tool: RequiredTool):
    contents = [("foo", "text for foo element"), ("bar", "more text for bar element")]
    hdca = target_history.with_list(contents)
    execute = required_tool.execute.with_inputs({"input1": hdca.src_dict})
    execute.assert_has_single_job.assert_has_single_output.with_contents_stripped("foo\nbar")


@requires_tool_id("identifier_in_actions")
def test_identifier_in_actions(target_history: TargetHistory, required_tool: RequiredTool):
    contents = [("foo", "text for foo element"), ("bar", "more text for bar element")]
    hdca = target_history.with_list(contents)

    execute = required_tool.execute.with_inputs({"input": {"batch": True, "values": [hdca.src_dict]}})

    output = execute.assert_has_job(0).assert_has_single_output
    assert output.details["metadata_column_names"][1] == "foo", output.details

    output = execute.assert_has_job(1).assert_has_single_output
    assert output.details["metadata_column_names"][1] == "bar", output.details


@requires_tool_id("identifier_single_in_repeat")
def test_identifier_single_in_repeat(target_history: TargetHistory, required_tool: RequiredTool):
    hdca = target_history.with_pair()
    execute = required_tool.execute.with_inputs(
        {"the_repeat_0|the_data|input1": {"batch": True, "values": [hdca.src_dict]}}
    )
    execute.assert_has_n_jobs(2).assert_creates_n_implicit_collections(1)
    output_collection = execute.assert_creates_implicit_collection(0)
    output_collection.assert_has_dataset_element("forward").with_contents_stripped("forward")
    output_collection.assert_has_dataset_element("reverse").with_contents_stripped("reverse")


@requires_tool_id("identifier_multiple_in_conditional")
def test_identifier_multiple_in_conditional(target_history: TargetHistory, required_tool: RequiredTool):
    hda = target_history.with_dataset("123", named="Normal HDA1")
    execute = required_tool.execute.with_inputs(
        {
            "outer_cond|inner_cond|input1": hda.src_dict,
        }
    )
    execute.assert_has_single_job.assert_has_single_output.with_contents_stripped("Normal HDA1")


@requires_tool_id("identifier_multiple")
def test_identifier_with_multiple_normal_datasets(target_history: TargetHistory, required_tool: RequiredTool):
    hda1 = target_history.with_dataset("123", named="Normal HDA1")
    hda2 = target_history.with_dataset("456", named="Normal HDA2")
    execute = required_tool.execute.with_inputs({"input1": [hda1.src_dict, hda2.src_dict]})
    execute.assert_has_single_job.assert_has_single_output.with_contents_stripped("Normal HDA1\nNormal HDA2")


@requires_tool_id("cat1")
def test_map_over_empty_collection(target_history: TargetHistory, required_tool: RequiredTool):
    hdca = target_history.with_list([])
    inputs = {
        "input1": {"batch": True, "values": [hdca.src_dict]},
    }
    execute = required_tool.execute.with_inputs(inputs)
    execute.assert_has_n_jobs(0)
    execute.assert_creates_implicit_collection(0).named("Concatenate datasets on collection 1")


@requires_tool_id("gx_repeat_boolean_min")
def test_optional_repeats_with_mins_filled_id(target_history: TargetHistory, required_tool: RequiredTool):
    # we have a tool test for this but I wanted to verify it wasn't just the
    # tool test framework filling in a default. Creating a raw request here
    # verifies that currently select parameters don't require a selection.
    required_tool.execute.assert_has_single_job.with_single_output.containing("false").containing("length: 2")
