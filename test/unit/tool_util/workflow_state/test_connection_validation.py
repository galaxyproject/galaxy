"""Tests for galaxy.tool_util.workflow_state.connection_validation.

Tests the connection validation engine internals that aren't covered
by the fixture-based tests in test_connection_workflows.py.
Fixture workflows cover: direct matching, map-over, multi-data reduction,
collection_type_source, structured_like, incompatible types.
"""

from galaxy.tool_util.workflow_state.connection_validation import (
    validate_connections,
)
from galaxy.tool_util_models.parameters import (
    IntegerParameterModel,
    TextParameterModel,
)
from galaxy.tool_util_models.tool_outputs import (
    ToolOutputInteger,
)
from .connection_test_fixtures import (
    make_collection_input,
    make_data_input,
    make_data_output,
    make_input_step,
    make_native_workflow,
    make_parsed_tool,
    make_subworkflow_step,
    make_tool_step,
    MockGetToolInfo,
)


class TestConnectionValidation:
    """Tests that require programmatic construction (no real tool XML)."""

    def test_unresolved_tool_skips(self):
        """Unknown tool -> connections are skipped."""
        tool_info = MockGetToolInfo()
        wf = make_native_workflow(
            make_input_step("data_input"),
            make_tool_step("unknown_tool", input_connections={"input1": {"id": 0, "output_name": "output"}}),
        )
        result = validate_connections(wf, tool_info)
        assert result.valid
        conn = result.step_results[1].connections[0]
        assert conn.status == "skip"


class TestStepMapOver:
    def test_compatible_map_over_from_multiple_inputs(self):
        """Two inputs both contributing list map-over -> step maps over list."""
        tool_info = MockGetToolInfo()
        tool_info.register(
            "two_in",
            make_parsed_tool(
                "two_in", inputs=[make_data_input("in1"), make_data_input("in2")], outputs=[make_data_output("out1")]
            ),
        )
        wf = make_native_workflow(
            make_input_step("data_collection_input", tool_state='{"collection_type": "list"}'),
            make_input_step("data_collection_input", tool_state='{"collection_type": "list"}'),
            make_tool_step(
                "two_in",
                input_connections={
                    "in1": {"id": 0, "output_name": "output"},
                    "in2": {"id": 1, "output_name": "output"},
                },
            ),
        )
        result = validate_connections(wf, tool_info)
        assert result.valid
        assert result.step_results[2].map_over == "list"

    def test_mixed_direct_and_mapover(self):
        """One input direct match, one input map-over -> step maps over."""
        tool_info = MockGetToolInfo()
        tool_info.register(
            "mixed",
            make_parsed_tool(
                "mixed",
                inputs=[make_collection_input("coll_in", "paired"), make_data_input("data_in")],
                outputs=[make_data_output("out1")],
            ),
        )
        wf = make_native_workflow(
            make_input_step("data_collection_input", tool_state='{"collection_type": "paired"}'),
            make_input_step("data_input"),
            make_tool_step(
                "mixed",
                input_connections={
                    "coll_in": {"id": 0, "output_name": "output"},
                    "data_in": {"id": 1, "output_name": "output"},
                },
            ),
        )
        result = validate_connections(wf, tool_info)
        assert result.valid
        assert result.step_results[2].map_over is None

    def test_no_connections_no_map_over(self):
        """Steps with no connections have no map-over."""
        tool_info = MockGetToolInfo()
        wf = make_native_workflow(make_input_step("data_input"))
        result = validate_connections(wf, tool_info)
        assert result.step_results[0].map_over is None


class TestMapOverVariants:
    """Map-over variants not covered by fixtures."""

    def test_list_paired_over_paired_or_unpaired(self):
        tool_info = MockGetToolInfo()
        tool_info.register(
            "pou_tool",
            make_parsed_tool(
                "pou_tool",
                inputs=[make_collection_input("input1", "paired_or_unpaired")],
                outputs=[make_data_output("out1")],
            ),
        )
        wf = make_native_workflow(
            make_input_step("data_collection_input", tool_state='{"collection_type": "list:paired"}'),
            make_tool_step("pou_tool", input_connections={"input1": {"id": 0, "output_name": "output"}}),
        )
        result = validate_connections(wf, tool_info)
        assert result.valid
        assert result.step_results[1].connections[0].mapping == "list"

    def test_list_list_over_list_paired_or_unpaired(self):
        tool_info = MockGetToolInfo()
        tool_info.register(
            "lpou_tool",
            make_parsed_tool(
                "lpou_tool",
                inputs=[make_collection_input("input1", "list:paired_or_unpaired")],
                outputs=[make_data_output("out1")],
            ),
        )
        wf = make_native_workflow(
            make_input_step("data_collection_input", tool_state='{"collection_type": "list:list"}'),
            make_tool_step("lpou_tool", input_connections={"input1": {"id": 0, "output_name": "output"}}),
        )
        result = validate_connections(wf, tool_info)
        assert result.valid
        assert result.step_results[1].connections[0].mapping == "list"


class TestMultiDataReduction:
    """Multi-data edge case not covered by fixtures."""

    def test_sample_sheet_to_multi_data_ok(self):
        """sample_sheet (normalizes to list) -> data(multiple=True) -> ok."""
        tool_info = MockGetToolInfo()
        tool_info.register(
            "multi_cat",
            make_parsed_tool(
                "multi_cat", inputs=[make_data_input("inputs", multiple=True)], outputs=[make_data_output("out1")]
            ),
        )
        wf = make_native_workflow(
            make_input_step("data_collection_input", tool_state='{"collection_type": "sample_sheet"}'),
            make_tool_step("multi_cat", input_connections={"inputs": {"id": 0, "output_name": "output"}}),
        )
        result = validate_connections(wf, tool_info)
        assert result.valid
        conn = result.step_results[1].connections[0]
        assert conn.status == "ok"
        assert conn.mapping is None


class TestEndToEnd:
    def test_empty_workflow(self):
        result = validate_connections({"steps": {}}, MockGetToolInfo())
        assert result.valid
        assert len(result.step_results) == 0

    def test_input_only_workflow(self):
        wf = make_native_workflow(make_input_step("data_input"), make_input_step("data_collection_input"))
        result = validate_connections(wf, MockGetToolInfo())
        assert result.valid

    def test_three_step_chain(self):
        """input -> tool1 -> tool2, all matching types."""
        tool_info = MockGetToolInfo()
        for tid in ["t1", "t2"]:
            tool_info.register(
                tid, make_parsed_tool(tid, inputs=[make_data_input("input1")], outputs=[make_data_output("out1")])
            )
        wf = make_native_workflow(
            make_input_step("data_input"),
            make_tool_step("t1", input_connections={"input1": {"id": 0, "output_name": "output"}}),
            make_tool_step("t2", input_connections={"input1": {"id": 1, "output_name": "out1"}}),
        )
        result = validate_connections(wf, tool_info)
        assert result.valid

    def test_summary_counts(self):
        tool_info = MockGetToolInfo()
        tool_info.register(
            "cat", make_parsed_tool("cat", inputs=[make_data_input("input1")], outputs=[make_data_output("out1")])
        )
        wf = make_native_workflow(
            make_input_step("data_collection_input", tool_state='{"collection_type": "list"}'),
            make_tool_step("cat", input_connections={"input1": {"id": 0, "output_name": "output"}}),
        )
        result = validate_connections(wf, tool_info)
        s = result.summary
        assert s["ok"] == 1
        assert s["invalid"] == 0


# -- Subworkflow tests --


def _inner_workflow_with_exposed_output(*steps, workflow_outputs=None):
    """Build a native workflow dict with workflow_outputs on specified steps.

    workflow_outputs: list of (step_index, output_name, label) tuples
    """
    wf = make_native_workflow(*steps)
    if workflow_outputs:
        for step_idx, output_name, label in workflow_outputs:
            step = wf["steps"][str(step_idx)]
            step.setdefault("workflow_outputs", []).append({"output_name": output_name, "label": label})
    return wf


class TestSubworkflow:
    def test_basic_passthrough(self):
        """data_input -> subworkflow(data_input -> cat -> out) -> cat2."""
        tool_info = MockGetToolInfo()
        tool_info.register(
            "cat", make_parsed_tool("cat", inputs=[make_data_input("input1")], outputs=[make_data_output("out1")])
        )
        tool_info.register(
            "cat2", make_parsed_tool("cat2", inputs=[make_data_input("input1")], outputs=[make_data_output("out1")])
        )
        inner_wf = _inner_workflow_with_exposed_output(
            make_input_step("data_input"),
            make_tool_step("cat", input_connections={"input1": {"id": 0, "output_name": "output"}}),
            workflow_outputs=[(1, "out1", "inner_out")],
        )
        wf = make_native_workflow(
            make_input_step("data_input"),
            make_subworkflow_step(
                inner_wf,
                input_connections={"data_in": {"id": 0, "output_name": "output", "input_subworkflow_step_id": 0}},
            ),
            make_tool_step("cat2", input_connections={"input1": {"id": 1, "output_name": "inner_out"}}),
        )
        result = validate_connections(wf, tool_info)
        assert result.valid
        # Step 2 connects to subworkflow output "inner_out" -> should be ok
        conn = result.step_results[2].connections[0]
        assert conn.status == "ok"
        assert conn.mapping is None

    def test_collection_type_propagation(self):
        """list:paired input -> subworkflow with paired inner tool -> output resolves."""
        tool_info = MockGetToolInfo()
        tool_info.register(
            "paired_tool",
            make_parsed_tool(
                "paired_tool",
                inputs=[make_collection_input("input1", "paired")],
                outputs=[make_data_output("out1")],
            ),
        )
        tool_info.register(
            "cat", make_parsed_tool("cat", inputs=[make_data_input("input1")], outputs=[make_data_output("out1")])
        )
        inner_wf = _inner_workflow_with_exposed_output(
            make_input_step("data_collection_input", tool_state='{"collection_type": "list:paired"}'),
            make_tool_step("paired_tool", input_connections={"input1": {"id": 0, "output_name": "output"}}),
            workflow_outputs=[(1, "out1", "processed")],
        )
        wf = make_native_workflow(
            make_input_step("data_collection_input", tool_state='{"collection_type": "list:paired"}'),
            make_subworkflow_step(
                inner_wf,
                input_connections={"coll_in": {"id": 0, "output_name": "output", "input_subworkflow_step_id": 0}},
            ),
            # Downstream consumes subworkflow output "processed" — should be list (map-over)
            make_tool_step("cat", input_connections={"input1": {"id": 1, "output_name": "processed"}}),
        )
        result = validate_connections(wf, tool_info)
        assert result.valid
        # Inner: list:paired -> paired_tool maps over list, out1 becomes list
        # Outer step 2 receives list -> maps over data input -> ok
        conn = result.step_results[2].connections[0]
        assert conn.status == "ok"
        assert conn.mapping == "list"

    def test_map_over_inside_subworkflow(self):
        """Outer feeds list, inner expects dataset -> inner maps over -> exposed output is list."""
        tool_info = MockGetToolInfo()
        tool_info.register(
            "cat", make_parsed_tool("cat", inputs=[make_data_input("input1")], outputs=[make_data_output("out1")])
        )
        tool_info.register(
            "list_consumer",
            make_parsed_tool(
                "list_consumer",
                inputs=[make_collection_input("input1", "list")],
                outputs=[make_data_output("out1")],
            ),
        )
        inner_wf = _inner_workflow_with_exposed_output(
            make_input_step("data_input"),  # expects dataset
            make_tool_step("cat", input_connections={"input1": {"id": 0, "output_name": "output"}}),
            workflow_outputs=[(1, "out1", "inner_out")],
        )
        wf = make_native_workflow(
            make_input_step("data_collection_input", tool_state='{"collection_type": "list"}'),
            make_subworkflow_step(
                inner_wf,
                input_connections={"data_in": {"id": 0, "output_name": "output", "input_subworkflow_step_id": 0}},
            ),
            # Subworkflow gets list, inner maps over -> exposed output is list
            make_tool_step("list_consumer", input_connections={"input1": {"id": 1, "output_name": "inner_out"}}),
        )
        result = validate_connections(wf, tool_info)
        assert result.valid
        conn = result.step_results[2].connections[0]
        assert conn.status == "ok"
        assert conn.mapping is None  # list -> list direct match

    def test_nested_subworkflow(self):
        """Outer -> subworkflow -> inner subworkflow -> tool. Two levels."""
        tool_info = MockGetToolInfo()
        tool_info.register(
            "cat", make_parsed_tool("cat", inputs=[make_data_input("input1")], outputs=[make_data_output("out1")])
        )
        # Inner-inner workflow: data_input -> cat
        inner_inner_wf = _inner_workflow_with_exposed_output(
            make_input_step("data_input"),
            make_tool_step("cat", input_connections={"input1": {"id": 0, "output_name": "output"}}),
            workflow_outputs=[(1, "out1", "deep_out")],
        )
        # Inner workflow: data_input -> subworkflow(inner_inner) -> expose
        inner_wf = _inner_workflow_with_exposed_output(
            make_input_step("data_input"),
            make_subworkflow_step(
                inner_inner_wf,
                input_connections={"data_in": {"id": 0, "output_name": "output", "input_subworkflow_step_id": 0}},
            ),
            workflow_outputs=[(1, "deep_out", "mid_out")],
        )
        wf = make_native_workflow(
            make_input_step("data_input"),
            make_subworkflow_step(
                inner_wf,
                input_connections={"data_in": {"id": 0, "output_name": "output", "input_subworkflow_step_id": 0}},
            ),
            make_tool_step("cat", input_connections={"input1": {"id": 1, "output_name": "mid_out"}}),
        )
        result = validate_connections(wf, tool_info)
        assert result.valid
        conn = result.step_results[2].connections[0]
        assert conn.status == "ok"

    def test_unresolved_inner_tool_graceful(self):
        """Subworkflow with unknown tool -> exposed output unresolved -> downstream skips."""
        tool_info = MockGetToolInfo()
        tool_info.register(
            "cat", make_parsed_tool("cat", inputs=[make_data_input("input1")], outputs=[make_data_output("out1")])
        )
        inner_wf = _inner_workflow_with_exposed_output(
            make_input_step("data_input"),
            make_tool_step("unknown_tool", input_connections={"input1": {"id": 0, "output_name": "output"}}),
            workflow_outputs=[(1, "out1", "inner_out")],
        )
        wf = make_native_workflow(
            make_input_step("data_input"),
            make_subworkflow_step(
                inner_wf,
                input_connections={"data_in": {"id": 0, "output_name": "output", "input_subworkflow_step_id": 0}},
            ),
            make_tool_step("cat", input_connections={"input1": {"id": 1, "output_name": "inner_out"}}),
        )
        result = validate_connections(wf, tool_info)
        # Should not crash — downstream connection skips because output type unknown
        assert result.valid  # skips are not failures
        conn = result.step_results[2].connections[0]
        assert conn.status == "skip"


# -- Parameter connection tests --


def _make_text_input(name="text_in"):
    return TextParameterModel(
        name=name,
        parameter_type="gx_text",
        type="text",
        hidden=False,
        is_dynamic=False,
        optional=False,
    )


def _make_integer_input(name="int_in"):
    return IntegerParameterModel(
        name=name,
        parameter_type="gx_integer",
        type="integer",
        hidden=False,
        is_dynamic=False,
        optional=False,
        value=0,
    )


class TestParameterConnections:
    """Tests for non-data (parameter) connections."""

    def test_parameter_input_to_text_param(self):
        """parameter_input(text) -> tool text param: ok, no skip."""
        tool_info = MockGetToolInfo()
        tool_info.register(
            "text_tool",
            make_parsed_tool(
                "text_tool",
                inputs=[_make_text_input("text_in")],
                outputs=[make_data_output("out1")],
            ),
        )
        wf = make_native_workflow(
            make_input_step("parameter_input", tool_state='{"parameter_type": "text"}'),
            make_tool_step("text_tool", input_connections={"text_in": {"id": 0, "output_name": "output"}}),
        )
        result = validate_connections(wf, tool_info)
        assert result.valid
        conn = result.step_results[1].connections[0]
        assert conn.status == "ok"

    def test_expression_tool_integer_output(self):
        """Tool with integer output -> downstream integer param: ok."""
        tool_info = MockGetToolInfo()
        tool_info.register(
            "expr_tool",
            make_parsed_tool(
                "expr_tool",
                inputs=[make_data_input("input1")],
                outputs=[ToolOutputInteger(name="int_out", type="integer", hidden=False)],
            ),
        )
        tool_info.register(
            "int_consumer",
            make_parsed_tool(
                "int_consumer",
                inputs=[_make_integer_input("int_in")],
                outputs=[make_data_output("out1")],
            ),
        )
        wf = make_native_workflow(
            make_input_step("data_input"),
            make_tool_step("expr_tool", input_connections={"input1": {"id": 0, "output_name": "output"}}),
            make_tool_step("int_consumer", input_connections={"int_in": {"id": 1, "output_name": "int_out"}}),
        )
        result = validate_connections(wf, tool_info)
        assert result.valid
        conn = result.step_results[2].connections[0]
        assert conn.status == "ok"

    def test_parameter_input_to_subworkflow_parameter(self):
        """parameter_input -> subworkflow with parameter_input inner step: ok."""
        tool_info = MockGetToolInfo()
        tool_info.register(
            "cat",
            make_parsed_tool(
                "cat",
                inputs=[_make_text_input("text_in")],
                outputs=[make_data_output("out1")],
            ),
        )
        inner_wf = _inner_workflow_with_exposed_output(
            make_input_step("parameter_input", tool_state='{"parameter_type": "text"}'),
            make_tool_step("cat", input_connections={"text_in": {"id": 0, "output_name": "output"}}),
            workflow_outputs=[(1, "out1", "inner_out")],
        )
        wf = make_native_workflow(
            make_input_step("parameter_input", tool_state='{"parameter_type": "text"}'),
            make_subworkflow_step(
                inner_wf,
                input_connections={"param_in": {"id": 0, "output_name": "output", "input_subworkflow_step_id": 0}},
            ),
        )
        result = validate_connections(wf, tool_info)
        assert result.valid
        conn = result.step_results[1].connections[0]
        assert conn.status == "ok"

    def test_mixed_data_and_parameter_connections(self):
        """Step with both data and parameter inputs validates both."""
        tool_info = MockGetToolInfo()
        tool_info.register(
            "mixed_tool",
            make_parsed_tool(
                "mixed_tool",
                inputs=[make_data_input("data_in"), _make_text_input("text_in")],
                outputs=[make_data_output("out1")],
            ),
        )
        wf = make_native_workflow(
            make_input_step("data_input"),
            make_input_step("parameter_input", tool_state='{"parameter_type": "text"}'),
            make_tool_step(
                "mixed_tool",
                input_connections={
                    "data_in": {"id": 0, "output_name": "output"},
                    "text_in": {"id": 1, "output_name": "output"},
                },
            ),
        )
        result = validate_connections(wf, tool_info)
        assert result.valid
        assert len(result.step_results[2].connections) == 2
        assert all(c.status == "ok" for c in result.step_results[2].connections)

    def test_subworkflow_data_collection_input_synthesized(self):
        """Subworkflow with data_collection_input inner step gets typed input."""
        tool_info = MockGetToolInfo()
        tool_info.register(
            "cat",
            make_parsed_tool("cat", inputs=[make_data_input("input1")], outputs=[make_data_output("out1")]),
        )
        inner_wf = _inner_workflow_with_exposed_output(
            make_input_step("data_collection_input", tool_state='{"collection_type": "list"}'),
            make_tool_step("cat", input_connections={"input1": {"id": 0, "output_name": "output"}}),
            workflow_outputs=[(1, "out1", "inner_out")],
        )
        wf = make_native_workflow(
            make_input_step("data_collection_input", tool_state='{"collection_type": "list"}'),
            make_subworkflow_step(
                inner_wf,
                input_connections={"coll_in": {"id": 0, "output_name": "output", "input_subworkflow_step_id": 0}},
            ),
        )
        result = validate_connections(wf, tool_info)
        assert result.valid
        conn = result.step_results[1].connections[0]
        assert conn.status == "ok"

    def test_when_conditional_execution(self):
        """boolean parameter_input -> tool step 'when': ok."""
        tool_info = MockGetToolInfo()
        tool_info.register(
            "cat",
            make_parsed_tool(
                "cat",
                inputs=[make_data_input("input1")],
                outputs=[make_data_output("out1")],
            ),
        )
        wf = make_native_workflow(
            make_input_step("parameter_input", tool_state='{"parameter_type": "boolean"}'),
            make_input_step("data_input"),
            {
                "type": "tool",
                "tool_id": "cat",
                "tool_version": "1.0",
                "when": "$(inputs.when)",
                "input_connections": {
                    "input1": {"id": 1, "output_name": "output"},
                    "when": {"id": 0, "output_name": "output"},
                },
            },
        )
        result = validate_connections(wf, tool_info)
        assert result.valid
        step_result = result.step_results[2]
        statuses = {c.target_input: c.status for c in step_result.connections}
        assert statuses["input1"] == "ok"
        assert statuses["when"] == "ok"
