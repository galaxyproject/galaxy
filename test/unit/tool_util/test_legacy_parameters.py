"""Tests for legacy replacement parameter classification in workflow tool state."""

from galaxy.tool_util.parameters import input_models_for_tool_source
from galaxy.tool_util.parser import get_tool_source
from galaxy.tool_util.unittest_utils.parameters import parameter_bundle_for_file
from galaxy.tool_util.workflow_state.legacy_parameters import (
    ReplacementClassification,
    scan_format2_state,
    scan_native_state,
)
from galaxy.util import galaxy_directory


def _random_lines_inputs():
    path = galaxy_directory() + "/tools/filters/randomlines.xml"
    tool_source = get_tool_source(path, macro_paths=[])
    bundle = input_models_for_tool_source(tool_source)
    return list(bundle.parameters)


def _simple_inputs(basename: str):
    bundle = parameter_bundle_for_file(basename)
    return list(bundle.parameters)


class TestScanNativeState:
    """Tests using random_lines1 tool: num_lines (integer), input (data),
    seed_source conditional with seed_source_selector (select) and seed (text)."""

    def test_yes_integer_replacement(self):
        inputs = _random_lines_inputs()
        tool_state = {
            "num_lines": "${num}",
            "input": {"__class__": "RuntimeValue"},
            "seed_source": {"seed_source_selector": "no_seed"},
        }
        result = scan_native_state(inputs, tool_state, input_connections={})
        assert result.classification == ReplacementClassification.YES
        assert len(result.hits) == 1
        assert result.hits[0].parameter_type == "gx_integer"
        assert result.hits[0].state_path == "num_lines"
        assert result.hits[0].value == "${num}"

    def test_yes_integer_and_maybe_text(self):
        inputs = _random_lines_inputs()
        tool_state = {
            "num_lines": "${num}",
            "input": {"__class__": "RuntimeValue"},
            "seed_source": {"seed_source_selector": "set_seed", "seed": "${seed}"},
        }
        result = scan_native_state(inputs, tool_state, input_connections={})
        assert result.classification == ReplacementClassification.YES
        assert len(result.hits) == 2
        types = {h.parameter_type for h in result.hits}
        assert types == {"gx_integer", "gx_text"}
        classifications = {h.classification for h in result.hits}
        assert ReplacementClassification.YES in classifications
        assert ReplacementClassification.MAYBE_ASSUMED_NO in classifications

    def test_maybe_text_only(self):
        inputs = _random_lines_inputs()
        tool_state = {
            "num_lines": "5",
            "input": {"__class__": "RuntimeValue"},
            "seed_source": {"seed_source_selector": "set_seed", "seed": "${seed}"},
        }
        result = scan_native_state(inputs, tool_state, input_connections={})
        assert result.classification == ReplacementClassification.MAYBE_ASSUMED_NO
        assert len(result.hits) == 1
        assert result.hits[0].parameter_type == "gx_text"

    def test_no_replacements(self):
        inputs = _random_lines_inputs()
        tool_state = {
            "num_lines": "5",
            "input": {"__class__": "RuntimeValue"},
            "seed_source": {"seed_source_selector": "no_seed"},
        }
        result = scan_native_state(inputs, tool_state, input_connections={})
        assert result.classification == ReplacementClassification.NO
        assert len(result.hits) == 0

    def test_maybe_text_with_literal_dollar_brace(self):
        """Text field containing ${ is MAYBE — could be literal text."""
        inputs = _random_lines_inputs()
        tool_state = {
            "num_lines": "5",
            "input": {"__class__": "RuntimeValue"},
            "seed_source": {"seed_source_selector": "set_seed", "seed": "literal ${braces} in text"},
        }
        result = scan_native_state(inputs, tool_state, input_connections={})
        assert result.classification == ReplacementClassification.MAYBE_ASSUMED_NO

    def test_runtime_value_skipped(self):
        """RuntimeValue markers should not be scanned for replacement params."""
        inputs = _random_lines_inputs()
        tool_state = {
            "num_lines": "5",
            "input": {"__class__": "RuntimeValue"},
            "seed_source": {"seed_source_selector": "no_seed"},
        }
        result = scan_native_state(inputs, tool_state, input_connections={})
        assert result.classification == ReplacementClassification.NO

    def test_hash_syntax_not_detected(self):
        """#{...} is PJA-only syntax, not a tool state replacement param."""
        inputs = _random_lines_inputs()
        tool_state = {
            "num_lines": "#{num}",
            "input": {"__class__": "RuntimeValue"},
            "seed_source": {"seed_source_selector": "no_seed"},
        }
        result = scan_native_state(inputs, tool_state, input_connections={})
        assert result.classification == ReplacementClassification.NO


class TestScanFormat2State:
    """Format2 state tests — same tool, but state values are typed (int, not str)
    unless replacement params passed through as strings."""

    def test_yes_integer_replacement(self):
        inputs = _random_lines_inputs()
        state = {"num_lines": "${num}", "seed_source": {"seed_source_selector": "no_seed"}}
        result = scan_format2_state(inputs, state)
        assert result.classification == ReplacementClassification.YES
        assert len(result.hits) == 1
        assert result.hits[0].parameter_type == "gx_integer"

    def test_no_normal_typed_values(self):
        inputs = _random_lines_inputs()
        state = {"num_lines": 5, "seed_source": {"seed_source_selector": "no_seed"}}
        result = scan_format2_state(inputs, state)
        assert result.classification == ReplacementClassification.NO

    def test_no_integer_is_int_not_string(self):
        """After proper conversion, integers are ints — no false positives."""
        inputs = _random_lines_inputs()
        state = {"num_lines": 42}
        result = scan_format2_state(inputs, state)
        assert result.classification == ReplacementClassification.NO

    def test_empty_state(self):
        inputs = _random_lines_inputs()
        result = scan_format2_state(inputs, {})
        assert result.classification == ReplacementClassification.NO

    def test_maybe_text_in_conditional(self):
        inputs = _random_lines_inputs()
        state = {
            "num_lines": 5,
            "seed_source": {"seed_source_selector": "set_seed", "seed": "${seed}"},
        }
        result = scan_format2_state(inputs, state)
        assert result.classification == ReplacementClassification.MAYBE_ASSUMED_NO


class TestSimpleParameterTypes:
    """YES classification for typed parameters using isolated test tools."""

    def test_float_replacement(self):
        inputs = _simple_inputs("gx_float")
        result = scan_format2_state(inputs, {"parameter": "${threshold}"})
        assert result.classification == ReplacementClassification.YES
        assert result.hits[0].parameter_type == "gx_float"

    def test_boolean_replacement(self):
        inputs = _simple_inputs("gx_boolean")
        result = scan_format2_state(inputs, {"parameter": "${flag}"})
        assert result.classification == ReplacementClassification.YES
        assert result.hits[0].parameter_type == "gx_boolean"

    def test_select_replacement(self):
        inputs = _simple_inputs("gx_select")
        result = scan_format2_state(inputs, {"parameter": "${choice}"})
        assert result.classification == ReplacementClassification.YES
        assert result.hits[0].parameter_type == "gx_select"

    def test_data_column_replacement(self):
        inputs = _simple_inputs("gx_data_column")
        result = scan_format2_state(inputs, {"parameter": "${col}"})
        assert result.classification == ReplacementClassification.YES
        assert result.hits[0].parameter_type == "gx_data_column"

    def test_text_replacement_is_maybe(self):
        inputs = _simple_inputs("gx_text")
        result = scan_format2_state(inputs, {"parameter": "${value}"})
        assert result.classification == ReplacementClassification.MAYBE_ASSUMED_NO
        assert result.hits[0].parameter_type == "gx_text"

    def test_int_replacement(self):
        inputs = _simple_inputs("gx_int")
        result = scan_format2_state(inputs, {"parameter": "${num}"})
        assert result.classification == ReplacementClassification.YES
        assert result.hits[0].parameter_type == "gx_integer"

    def test_int_normal_value_no_hit(self):
        inputs = _simple_inputs("gx_int")
        result = scan_format2_state(inputs, {"parameter": 5})
        assert result.classification == ReplacementClassification.NO

    def test_float_normal_value_no_hit(self):
        inputs = _simple_inputs("gx_float")
        result = scan_format2_state(inputs, {"parameter": 1.5})
        assert result.classification == ReplacementClassification.NO

    def test_hidden_replacement_is_maybe(self):
        inputs = _simple_inputs("gx_hidden")
        result = scan_format2_state(inputs, {"parameter": "${secret}"})
        assert result.classification == ReplacementClassification.MAYBE_ASSUMED_NO
        assert result.hits[0].parameter_type == "gx_hidden"

    def test_hash_syntax_not_detected_format2(self):
        """#{...} is PJA-only syntax, not detected in tool state."""
        inputs = _simple_inputs("gx_int")
        result = scan_format2_state(inputs, {"parameter": "#{num}"})
        assert result.classification == ReplacementClassification.NO
