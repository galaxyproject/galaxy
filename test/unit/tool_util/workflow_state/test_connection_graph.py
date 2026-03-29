"""Tests for galaxy.tool_util.workflow_state.connection_graph.

Tests the workflow graph builder: step resolution, connection parsing,
data input/output extraction, and topological sort.
"""

import pytest
from gxformat2.normalized import NormalizedNativeStep

from galaxy.tool_util.parameters import (
    ConditionalParameterModel,
    ConditionalWhen,
    RepeatParameterModel,
    SelectParameterModel,
)
from galaxy.tool_util.workflow_state.connection_graph import (
    _collect_inputs,
    _collect_outputs,
    _parse_connections,
    _topological_sort,
    build_workflow_graph,
    ResolvedStep,
)
from galaxy.tool_util_models.parameters import (
    LabelValue,
    SectionParameterModel,
)
from galaxy.util.topsort import CycleError
from .connection_test_fixtures import (
    make_collection_input,
    make_collection_output,
    make_data_input,
    make_data_output,
    make_input_step,
    make_native_workflow,
    make_parsed_tool,
    make_subworkflow_step,
    make_tool_step,
    MockGetToolInfo,
)

# -- _parse_connections tests --


def _step_with_connections(input_connections=None):
    """Build a minimal NormalizedNativeStep with given input_connections."""
    return NormalizedNativeStep(
        id=0,
        type="tool",
        input_connections=input_connections or {},
    )


class TestParseConnections:
    def test_empty(self):
        result = _parse_connections(_step_with_connections({}))
        assert result == {}

    def test_no_input_connections_key(self):
        result = _parse_connections(_step_with_connections())
        assert result == {}

    def test_single_connection(self):
        step = _step_with_connections({"input1": {"id": 0, "output_name": "output"}})
        result = _parse_connections(step)
        assert "input1" in result
        assert len(result["input1"]) == 1
        assert result["input1"][0].source_step == "0"
        assert result["input1"][0].output_name == "output"

    def test_multiple_connections_to_same_input(self):
        step = _step_with_connections(
            {
                "input1": [
                    {"id": 0, "output_name": "output"},
                    {"id": 1, "output_name": "out2"},
                ]
            }
        )
        result = _parse_connections(step)
        assert len(result["input1"]) == 2
        assert result["input1"][0].source_step == "0"
        assert result["input1"][1].source_step == "1"
        assert result["input1"][1].output_name == "out2"

    def test_nested_state_path(self):
        step = _step_with_connections({"cond|inner_param": {"id": 0, "output_name": "output"}})
        result = _parse_connections(step)
        assert "cond|inner_param" in result

    def test_output_name_passthrough(self):
        step = _step_with_connections({"input1": {"id": 0, "output_name": "custom_out"}})
        result = _parse_connections(step)
        assert result["input1"][0].output_name == "custom_out"


# -- _collect_inputs tests --


class TestCollectDataInputs:
    def test_simple_data_input(self):
        params = [make_data_input("f1")]
        result = _collect_inputs(params)
        assert "f1" in result
        assert result["f1"].type == "data"
        assert not result["f1"].multiple

    def test_collection_input(self):
        params = [make_collection_input("f1", collection_type="paired")]
        result = _collect_inputs(params)
        assert "f1" in result
        assert result["f1"].type == "collection"
        assert result["f1"].collection_type == "paired"

    def test_multiple_data_input(self):
        params = [make_data_input("f1", multiple=True)]
        result = _collect_inputs(params)
        assert result["f1"].multiple

    def test_optional_input(self):
        params = [make_data_input("f1", optional=True)]
        result = _collect_inputs(params)
        assert result["f1"].optional

    def test_includes_parameter_inputs(self):
        params = [
            SelectParameterModel(
                name="select1",
                parameter_type="gx_select",
                type="select",
                hidden=False,
                is_dynamic=False,
                optional=False,
                multiple=False,
                options=[],
            ),
            make_data_input("f1"),
        ]
        result = _collect_inputs(params)
        assert len(result) == 2
        assert "f1" in result
        assert result["f1"].type == "data"
        assert "select1" in result
        assert result["select1"].type == "select"

    def test_conditional_walks_active_case(self):
        cond = ConditionalParameterModel(
            name="cond1",
            parameter_type="gx_conditional",
            type="conditional",
            hidden=False,
            is_dynamic=False,
            optional=False,
            test_parameter=SelectParameterModel(
                name="test_param",
                parameter_type="gx_select",
                type="select",
                hidden=False,
                is_dynamic=False,
                optional=False,
                multiple=False,
                options=[
                    LabelValue(value="yes", label="Yes", selected=False),
                    LabelValue(value="no", label="No", selected=False),
                ],
            ),
            whens=[
                ConditionalWhen(
                    discriminator="yes",
                    parameters=[make_data_input("data_yes")],
                    is_default_when=False,
                ),
                ConditionalWhen(
                    discriminator="no",
                    parameters=[make_data_input("data_no")],
                    is_default_when=False,
                ),
            ],
        )
        # Active case: test_param=yes -> only "yes" branch
        tool_state = {"cond1": {"test_param": "yes"}}
        result = _collect_inputs([cond], tool_state)
        assert "cond1|data_yes" in result
        assert "cond1|data_no" not in result

    def test_conditional_walks_all_when_no_state(self):
        cond = ConditionalParameterModel(
            name="cond1",
            parameter_type="gx_conditional",
            type="conditional",
            hidden=False,
            is_dynamic=False,
            optional=False,
            test_parameter=SelectParameterModel(
                name="test_param",
                parameter_type="gx_select",
                type="select",
                hidden=False,
                is_dynamic=False,
                optional=False,
                multiple=False,
                options=[],
            ),
            whens=[
                ConditionalWhen(
                    discriminator="a",
                    parameters=[make_data_input("data_a")],
                    is_default_when=False,
                ),
                ConditionalWhen(
                    discriminator="b",
                    parameters=[make_data_input("data_b")],
                    is_default_when=False,
                ),
            ],
        )
        result = _collect_inputs([cond], None)
        assert "cond1|data_a" in result
        assert "cond1|data_b" in result

    def test_section(self):
        section = SectionParameterModel(
            name="sec1",
            parameter_type="gx_section",
            type="section",
            hidden=False,
            is_dynamic=False,
            optional=False,
            parameters=[make_data_input("inner")],
        )
        result = _collect_inputs([section])
        assert "sec1|inner" in result

    def test_repeat(self):
        repeat = RepeatParameterModel(
            name="rep1",
            parameter_type="gx_repeat",
            type="repeat",
            hidden=False,
            is_dynamic=False,
            optional=False,
            parameters=[make_data_input("item")],
            min=0,
            max=None,
            default=0,
        )
        result = _collect_inputs([repeat])
        assert "rep1|item" in result


# -- _collect_outputs tests --


class TestCollectOutputs:
    def test_data_output(self):
        outputs = [make_data_output("out1", format="bam")]
        result = _collect_outputs(outputs)
        assert "out1" in result
        assert result["out1"].type == "data"
        assert result["out1"].format == "bam"

    def test_collection_output(self):
        outputs = [make_collection_output("out1", collection_type="list:paired")]
        result = _collect_outputs(outputs)
        assert "out1" in result
        assert result["out1"].type == "collection"
        assert result["out1"].collection_type == "list:paired"

    def test_collection_type_source(self):
        outputs = [make_collection_output("out1", collection_type_source="input1")]
        result = _collect_outputs(outputs)
        assert result["out1"].collection_type_source == "input1"

    def test_structured_like(self):
        outputs = [make_collection_output("out1", structured_like="input1")]
        result = _collect_outputs(outputs)
        assert result["out1"].structured_like == "input1"

    def test_format_source(self):
        from galaxy.tool_util_models.tool_outputs import ToolOutputDataset

        outputs = [ToolOutputDataset(name="out1", type="data", format="data", format_source="input1", hidden=False)]
        result = _collect_outputs(outputs)
        assert result["out1"].format_source == "input1"

    def test_includes_non_data_outputs(self):
        from galaxy.tool_util_models.tool_outputs import ToolOutputText

        outputs = [make_data_output("out1"), ToolOutputText(name="text_out", type="text", hidden=False)]
        result = _collect_outputs(outputs)
        assert len(result) == 2
        assert "out1" in result
        assert result["out1"].type == "data"
        assert "text_out" in result
        assert result["text_out"].type == "text"

    def test_multiple_outputs(self):
        outputs = [make_data_output("out1"), make_collection_output("out2", collection_type="list")]
        result = _collect_outputs(outputs)
        assert len(result) == 2


# -- Input step resolution tests --


class TestResolveInputStep:
    def test_data_input_step(self):
        tool_info = MockGetToolInfo()
        wf = make_native_workflow(make_input_step("data_input"))
        graph = build_workflow_graph(wf, tool_info)
        step = graph.steps["0"]
        assert step.step_type == "data_input"
        assert "output" in step.outputs
        assert step.outputs["output"].type == "data"

    def test_data_collection_input_step(self):
        tool_info = MockGetToolInfo()
        wf = make_native_workflow(
            make_input_step("data_collection_input", tool_state='{"collection_type": "list:paired"}')
        )
        graph = build_workflow_graph(wf, tool_info)
        step = graph.steps["0"]
        assert step.step_type == "data_collection_input"
        assert step.declared_collection_type == "list:paired"
        assert step.outputs["output"].type == "collection"
        assert step.outputs["output"].collection_type == "list:paired"

    def test_data_collection_input_default_list(self):
        tool_info = MockGetToolInfo()
        wf = make_native_workflow(make_input_step("data_collection_input", tool_state="{}"))
        graph = build_workflow_graph(wf, tool_info)
        assert graph.steps["0"].declared_collection_type == "list"

    def test_parameter_input_step(self):
        tool_info = MockGetToolInfo()
        wf = make_native_workflow(make_input_step("parameter_input", tool_state='{"parameter_type": "integer"}'))
        graph = build_workflow_graph(wf, tool_info)
        step = graph.steps["0"]
        assert step.step_type == "parameter_input"
        assert "output" in step.outputs
        assert step.outputs["output"].type == "integer"

    def test_parameter_input_step_default_text(self):
        tool_info = MockGetToolInfo()
        wf = make_native_workflow(make_input_step("parameter_input"))
        graph = build_workflow_graph(wf, tool_info)
        step = graph.steps["0"]
        assert step.outputs["output"].type == "text"

    def test_pause_step(self):
        tool_info = MockGetToolInfo()
        wf = make_native_workflow({"type": "pause"})
        graph = build_workflow_graph(wf, tool_info)
        assert graph.steps["0"].step_type == "pause"


# -- Tool step resolution tests --


class TestResolveToolStep:
    def test_basic_tool_step(self):
        tool_info = MockGetToolInfo()
        tool_info.register(
            "cat",
            make_parsed_tool("cat", inputs=[make_data_input("input1")], outputs=[make_data_output("out1")]),
        )
        wf = make_native_workflow(
            make_input_step("data_input"),
            make_tool_step("cat", input_connections={"input1": {"id": 0, "output_name": "output"}}),
        )
        graph = build_workflow_graph(wf, tool_info)
        tool_step = graph.steps["1"]
        assert tool_step.tool_id == "cat"
        assert "input1" in tool_step.inputs
        assert "out1" in tool_step.outputs
        assert "input1" in tool_step.connections
        assert tool_step.connections["input1"][0].source_step == "0"

    def test_tool_with_collection_io(self):
        tool_info = MockGetToolInfo()
        tool_info.register(
            "paired_tool",
            make_parsed_tool(
                "paired_tool",
                inputs=[make_collection_input("input1", "paired")],
                outputs=[make_collection_output("out1", collection_type="paired")],
            ),
        )
        wf = make_native_workflow(
            make_input_step("data_collection_input", tool_state='{"collection_type": "list:paired"}'),
            make_tool_step("paired_tool", input_connections={"input1": {"id": 0, "output_name": "output"}}),
        )
        graph = build_workflow_graph(wf, tool_info)
        tool_step = graph.steps["1"]
        assert tool_step.inputs["input1"].type == "collection"
        assert tool_step.inputs["input1"].collection_type == "paired"
        assert tool_step.outputs["out1"].type == "collection"
        assert tool_step.outputs["out1"].collection_type == "paired"

    def test_tool_not_found_graceful(self):
        """Steps with unknown tools get empty inputs/outputs but keep connections."""
        tool_info = MockGetToolInfo()
        wf = make_native_workflow(
            make_input_step("data_input"),
            make_tool_step("unknown_tool", input_connections={"input1": {"id": 0, "output_name": "output"}}),
        )
        graph = build_workflow_graph(wf, tool_info)
        tool_step = graph.steps["1"]
        assert tool_step.tool_id == "unknown_tool"
        assert len(tool_step.inputs) == 0
        assert len(tool_step.outputs) == 0
        assert "input1" in tool_step.connections

    def test_tool_with_collection_type_source(self):
        tool_info = MockGetToolInfo()
        tool_info.register(
            "pass_through",
            make_parsed_tool(
                "pass_through",
                inputs=[make_collection_input("input1", collection_type=None)],
                outputs=[make_collection_output("out1", collection_type_source="input1")],
            ),
        )
        wf = make_native_workflow(
            make_input_step("data_collection_input", tool_state='{"collection_type": "list"}'),
            make_tool_step("pass_through", input_connections={"input1": {"id": 0, "output_name": "output"}}),
        )
        graph = build_workflow_graph(wf, tool_info)
        assert graph.steps["1"].outputs["out1"].collection_type_source == "input1"

    def test_multi_data_input(self):
        tool_info = MockGetToolInfo()
        tool_info.register(
            "multi_cat",
            make_parsed_tool(
                "multi_cat", inputs=[make_data_input("inputs", multiple=True)], outputs=[make_data_output("out1")]
            ),
        )
        wf = make_native_workflow(
            make_input_step("data_input"),
            make_tool_step(
                "multi_cat",
                input_connections={
                    "inputs": [
                        {"id": 0, "output_name": "output"},
                        {"id": 0, "output_name": "output"},
                    ]
                },
            ),
        )
        graph = build_workflow_graph(wf, tool_info)
        assert graph.steps["1"].inputs["inputs"].multiple
        assert len(graph.steps["1"].connections["inputs"]) == 2


# -- Topological sort tests --


class TestTopologicalSort:
    def test_linear_chain(self):
        steps = {
            "0": ResolvedStep(step_id="0", tool_id=None, step_type="data_input"),
            "1": ResolvedStep(step_id="1", tool_id="t1", step_type="tool"),
            "2": ResolvedStep(step_id="2", tool_id="t2", step_type="tool"),
        }
        from galaxy.tool_util.workflow_state.connection_graph import ConnectionRef

        steps["1"].connections = {"in": [ConnectionRef("0", "output")]}
        steps["2"].connections = {"in": [ConnectionRef("1", "output")]}
        result = _topological_sort(steps)
        assert result.index("0") < result.index("1")
        assert result.index("1") < result.index("2")

    def test_diamond(self):
        steps = {
            "0": ResolvedStep(step_id="0", tool_id=None, step_type="data_input"),
            "1": ResolvedStep(step_id="1", tool_id="t1", step_type="tool"),
            "2": ResolvedStep(step_id="2", tool_id="t2", step_type="tool"),
            "3": ResolvedStep(step_id="3", tool_id="t3", step_type="tool"),
        }
        from galaxy.tool_util.workflow_state.connection_graph import ConnectionRef

        steps["1"].connections = {"in": [ConnectionRef("0", "output")]}
        steps["2"].connections = {"in": [ConnectionRef("0", "output")]}
        steps["3"].connections = {
            "in1": [ConnectionRef("1", "output")],
            "in2": [ConnectionRef("2", "output")],
        }
        result = _topological_sort(steps)
        assert result.index("0") < result.index("1")
        assert result.index("0") < result.index("2")
        assert result.index("1") < result.index("3")
        assert result.index("2") < result.index("3")

    def test_disconnected_steps(self):
        steps = {
            "0": ResolvedStep(step_id="0", tool_id=None, step_type="data_input"),
            "1": ResolvedStep(step_id="1", tool_id=None, step_type="data_input"),
        }
        result = _topological_sort(steps)
        assert set(result) == {"0", "1"}

    def test_cycle_detection(self):
        from galaxy.tool_util.workflow_state.connection_graph import ConnectionRef

        steps = {
            "0": ResolvedStep(step_id="0", tool_id="t1", step_type="tool"),
            "1": ResolvedStep(step_id="1", tool_id="t2", step_type="tool"),
        }
        steps["0"].connections = {"in": [ConnectionRef("1", "output")]}
        steps["1"].connections = {"in": [ConnectionRef("0", "output")]}
        with pytest.raises(CycleError):
            _topological_sort(steps)


# -- End-to-end build_workflow_graph tests --


class TestBuildWorkflowGraph:
    def test_simple_two_step(self):
        tool_info = MockGetToolInfo()
        tool_info.register(
            "cat",
            make_parsed_tool("cat", inputs=[make_data_input("input1")], outputs=[make_data_output("out1")]),
        )
        wf = make_native_workflow(
            make_input_step("data_input"),
            make_tool_step("cat", input_connections={"input1": {"id": 0, "output_name": "output"}}),
        )
        graph = build_workflow_graph(wf, tool_info)
        assert len(graph.steps) == 2
        assert graph.sorted_step_ids == ["0", "1"]

    def test_three_step_chain(self):
        tool_info = MockGetToolInfo()
        for tid in ["t1", "t2"]:
            tool_info.register(
                tid,
                make_parsed_tool(tid, inputs=[make_data_input("input1")], outputs=[make_data_output("out1")]),
            )
        wf = make_native_workflow(
            make_input_step("data_input"),
            make_tool_step("t1", input_connections={"input1": {"id": 0, "output_name": "output"}}),
            make_tool_step("t2", input_connections={"input1": {"id": 1, "output_name": "out1"}}),
        )
        graph = build_workflow_graph(wf, tool_info)
        assert graph.sorted_step_ids == ["0", "1", "2"]

    def test_subworkflow_step_preserves_connections(self):
        tool_info = MockGetToolInfo()
        inner_wf = make_native_workflow()
        wf = make_native_workflow(
            make_input_step("data_input"),
            make_subworkflow_step(inner_wf, input_connections={"input1": {"id": 0, "output_name": "output"}}),
        )
        graph = build_workflow_graph(wf, tool_info)
        assert graph.steps["1"].step_type == "subworkflow"
        assert "input1" in graph.steps["1"].connections

    def test_collection_workflow(self):
        """Realistic: collection input -> tool expecting paired -> output."""
        tool_info = MockGetToolInfo()
        tool_info.register(
            "paired_tool",
            make_parsed_tool(
                "paired_tool",
                inputs=[make_collection_input("input1", "paired")],
                outputs=[make_data_output("out1")],
            ),
        )
        wf = make_native_workflow(
            make_input_step("data_collection_input", tool_state='{"collection_type": "list:paired"}'),
            make_tool_step("paired_tool", input_connections={"input1": {"id": 0, "output_name": "output"}}),
        )
        graph = build_workflow_graph(wf, tool_info)
        assert graph.steps["0"].outputs["output"].collection_type == "list:paired"
        assert graph.steps["1"].inputs["input1"].collection_type == "paired"
        assert graph.sorted_step_ids.index("0") < graph.sorted_step_ids.index("1")

    def test_empty_workflow(self):
        graph = build_workflow_graph(make_native_workflow(), MockGetToolInfo())
        assert len(graph.steps) == 0
        assert len(graph.sorted_step_ids) == 0

    def test_tool_state_as_json_string(self):
        """tool_state can be a JSON string (double-encoded in native format)."""
        tool_info = MockGetToolInfo()
        wf = make_native_workflow(
            make_input_step("data_collection_input", tool_state='{"collection_type": "paired"}'),
        )
        graph = build_workflow_graph(wf, tool_info)
        assert graph.steps["0"].declared_collection_type == "paired"

    def test_tool_state_as_dict(self):
        """tool_state can also be an already-decoded dict."""
        tool_info = MockGetToolInfo()
        wf = make_native_workflow(
            make_input_step("data_collection_input", tool_state={"collection_type": "paired"}),
        )
        graph = build_workflow_graph(wf, tool_info)
        assert graph.steps["0"].declared_collection_type == "paired"
