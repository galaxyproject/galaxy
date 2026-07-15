"""Round-trip test harness for workflow state conversion.

Tests native→format2→native and format2→native→format2 round-trips,
cataloging failures by class to drive conversion library work.

Core comparison and round-trip logic lives in galaxy.tool_util.workflow_state.roundtrip;
this file contains test inventory, loaders, sweep runners, and pytest classes.
"""

import json
import os

import pytest
from gxformat2.converter import python_to_workflow
from gxformat2.yaml import ordered_load

from galaxy.tool_util.workflow_state.roundtrip import (
    _values_equivalent,
    classify_error,
    compare_tool_state,
    FailureClass,
    roundtrip_native_workflow,
    roundtrip_validate,
    RoundTripResult,
    RoundTripValidationResult,
    StepResult,
)
from galaxy.util import galaxy_directory
from galaxy.workflow.gx_validator import (
    GET_TOOL_INFO,
    GET_TOOL_INFO_WITH_TOOLSHED,
)

# -- Paths --

TEST_WORKFLOW_DIRECTORY = os.path.join(galaxy_directory(), "lib", "galaxy_test", "workflow")
TEST_BASE_DATA_DIRECTORY = os.path.join(galaxy_directory(), "lib", "galaxy_test", "base", "data")
SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))


# -- Loaders --


def _load(path: str) -> dict:
    with open(path) as f:
        return ordered_load(f)


def load_native_workflow(filename: str) -> dict:
    return _load(os.path.join(TEST_BASE_DATA_DIRECTORY, filename))


def load_framework_workflow(name: str) -> dict:
    return _load(os.path.join(TEST_WORKFLOW_DIRECTORY, f"{name}.gxwf.yml"))


def load_unit_workflow(name: str) -> dict:
    return _load(os.path.join(SCRIPT_DIRECTORY, f"{name}.gxwf.yml"))


# -- Test inventory --

EXCLUDED_WORKFLOWS = {
    "test_workflow_missing_tool.ga": "Intentionally references nonexistent tool 'cat_missing_tool'",
}

NATIVE_WORKFLOWS = [
    "test_workflow_1.ga",
    "test_workflow_2.ga",
    "test_workflow_two_random_lines.ga",
    "test_workflow_pause.ga",
    "test_workflow_batch.ga",
    "test_workflow_matching_lists.ga",
    "test_workflow_randomlines_legacy_params.ga",
    "test_workflow_randomlines_legacy_params_mixed_types.ga",
    "test_workflow_topoambigouity.ga",
    "test_workflow_topoambigouity_auto_laidout.ga",
    "test_workflow_map_reduce_pause.ga",
    "test_workflow_missing_tool.ga",
    "test_workflow_validation_1.ga",
    "test_workflow_with_input_tags.ga",
    "test_workflow_with_runtime_input.ga",
    "test_subworkflow_with_integer_input.ga",
    "test_subworkflow_with_tags.ga",
]

FRAMEWORK_WORKFLOWS = [
    "default_values",
    "default_values_optional",
    "directory_index",
    "empty_collection_sort",
    "filter_null",
    "flat_over_paired_or_unpaired",
    "flatten_collection",
    "flatten_collection_over_execution",
    "integer_into_data_column",
    "map_over_expression",
    "multi_select_mapping",
    "multiple_integer_into_data_column",
    "multiple_text",
    "multiple_versions",
    "optional_conditional_inputs_to_build_list",
    "optional_text_param_rescheduling",
    "output_parameter",
    "rename_based_on_input_collection",
    "replacement_parameters_legacy",
    "replacement_parameters_nested",
    "replacement_parameters_text",
    "subcollection_rank_sorting",
    "subcollection_rank_sorting_paired",
    "triply_nested_list_mapping",
    "zip_collection",
]

UNIT_WORKFLOWS = [
    "valid/simple_data",
    "valid/simple_int",
]


# -- Sweep functions --


def run_sweep(get_tool_info=None) -> dict[str, RoundTripResult]:
    """Run round-trip conversion sweep across all test workflows."""
    if get_tool_info is None:
        get_tool_info = GET_TOOL_INFO

    results: dict[str, RoundTripResult] = {}

    for filename in NATIVE_WORKFLOWS:
        if filename in EXCLUDED_WORKFLOWS:
            continue
        path = os.path.join(TEST_BASE_DATA_DIRECTORY, filename)
        if not os.path.exists(path):
            continue
        try:
            workflow = load_native_workflow(filename)
            result = roundtrip_native_workflow(workflow, get_tool_info, filename)
        except Exception as e:
            result = RoundTripResult(
                workflow_name=filename,
                direction="native_to_format2",
                step_results=[
                    StepResult(
                        step_id="load",
                        tool_id=None,
                        success=False,
                        failure_class=classify_error(e),
                        error=str(e),
                    )
                ],
            )
        results[f"native/{filename}"] = result

    for name in FRAMEWORK_WORKFLOWS:
        path = os.path.join(TEST_WORKFLOW_DIRECTORY, f"{name}.gxwf.yml")
        if not os.path.exists(path):
            continue
        try:
            workflow = load_framework_workflow(name)
            native = python_to_workflow(workflow, galaxy_interface=None)
            result = roundtrip_native_workflow(native, get_tool_info, name)
            result.direction = "format2_to_native_to_format2"
        except Exception as e:
            result = RoundTripResult(
                workflow_name=name,
                direction="format2_to_native_to_format2",
                step_results=[
                    StepResult(
                        step_id="convert",
                        tool_id=None,
                        success=False,
                        failure_class=classify_error(e),
                        error=str(e),
                    )
                ],
            )
        results[f"format2/{name}"] = result

    for name in UNIT_WORKFLOWS:
        try:
            workflow = load_unit_workflow(name)
            native = python_to_workflow(workflow, galaxy_interface=None)
            result = roundtrip_native_workflow(native, get_tool_info, name)
            result.direction = "format2_to_native_to_format2"
        except Exception as e:
            result = RoundTripResult(
                workflow_name=name,
                direction="format2_to_native_to_format2",
                step_results=[
                    StepResult(
                        step_id="convert",
                        tool_id=None,
                        success=False,
                        failure_class=classify_error(e),
                        error=str(e),
                    )
                ],
            )
        results[f"unit/{name}"] = result

    return results


def run_full_roundtrip_sweep(get_tool_info=None) -> dict[str, RoundTripValidationResult]:
    """Run full native→format2→native'→compare for all native workflows."""
    if get_tool_info is None:
        get_tool_info = GET_TOOL_INFO

    results: dict[str, RoundTripValidationResult] = {}

    for filename in NATIVE_WORKFLOWS:
        if filename in EXCLUDED_WORKFLOWS:
            continue
        path = os.path.join(TEST_BASE_DATA_DIRECTORY, filename)
        if not os.path.exists(path):
            continue
        try:
            workflow = load_native_workflow(filename)
            results[filename] = roundtrip_validate(workflow, get_tool_info, workflow_path=filename)
        except Exception as e:
            results[filename] = RoundTripValidationResult(
                workflow_path=filename,
                error=str(e),
            )

    return results


# -- Print functions --


def print_sweep_results(results: dict[str, RoundTripResult]):
    print(f"\n{'=' * 80}")
    print("Round-Trip Sweep Results")
    print(f"{'=' * 80}\n")

    if EXCLUDED_WORKFLOWS:
        print(f"EXCLUDED: {len(EXCLUDED_WORKFLOWS)}")
        for name, reason in sorted(EXCLUDED_WORKFLOWS.items()):
            print(f"  [SKIP] {name}: {reason}")
        print()

    passes = []
    failures = []
    for name, result in sorted(results.items()):
        if result.success:
            passes.append(name)
        else:
            failures.append((name, result))

    print(f"PASSED: {len(passes)}/{len(results)}")
    for name in passes:
        print(f"  [PASS] {name}")

    print(f"\nFAILED: {len(failures)}/{len(results)}")

    by_class: dict[str, list[tuple[str, str]]] = {}
    for name, result in failures:
        for sr in result.step_results:
            if not sr.success:
                fc = sr.failure_class.value if sr.failure_class else "unknown"
                by_class.setdefault(fc, []).append((name, f"step {sr.step_id} ({sr.tool_id}): {sr.error}"))

    for fc, items in sorted(by_class.items()):
        print(f"\n  [{fc}] ({len(items)} failures)")
        for name, detail in items:
            print(f"    {name}: {detail}")

    print(f"\n{'=' * 80}")


def print_full_roundtrip_results(results: dict[str, RoundTripValidationResult]):
    from galaxy.tool_util.workflow_state.roundtrip import format_validation_text

    print(f"\n{'=' * 80}")
    print("Full Round-Trip Sweep (native → format2 → native' → compare)")
    print(f"{'=' * 80}\n")
    print(format_validation_text(list(results.values()), verbose=True))
    print(f"\n{'=' * 80}")


# -- Pytest test classes --


class TestRoundTripSweep:
    """Run the sweep and report. This is the main entry point for cataloging failures."""

    def test_sweep_report(self):
        """Run per-step conversion sweep. Asserts all non-excluded workflows pass."""
        results = run_sweep()
        print_sweep_results(results)
        failures = {name: r for name, r in results.items() if not r.success}
        assert not failures, f"{len(failures)} workflow(s) failed per-step conversion: {list(failures.keys())}"

    def test_full_roundtrip_sweep(self):
        """Run full native→format2→native'→compare sweep. Asserts all non-excluded pass."""
        results = run_full_roundtrip_sweep()
        print_full_roundtrip_results(results)
        failures = {name: r for name, r in results.items() if not r.ok}
        assert not failures, f"{len(failures)} workflow(s) failed full round-trip: {list(failures.keys())}"


class TestNativeRoundTrip:
    """Test round-trip for native workflows that we expect to work."""

    def test_workflow_two_random_lines(self):
        workflow = load_native_workflow("test_workflow_two_random_lines.ga")
        result = roundtrip_native_workflow(workflow, GET_TOOL_INFO, "test_workflow_two_random_lines.ga")
        _assert_roundtrip_passes(result)

    def test_workflow_1(self):
        workflow = load_native_workflow("test_workflow_1.ga")
        result = roundtrip_native_workflow(workflow, GET_TOOL_INFO, "test_workflow_1.ga")
        _assert_roundtrip_passes(result)


class TestFullNativeRoundTrip:
    """Full round-trip: native → format2 → native' → compare."""

    def test_workflow_1(self):
        workflow = load_native_workflow("test_workflow_1.ga")
        result = roundtrip_validate(workflow, GET_TOOL_INFO, workflow_path="test_workflow_1.ga")
        _assert_validation_ok(result)

    def test_workflow_two_random_lines(self):
        workflow = load_native_workflow("test_workflow_two_random_lines.ga")
        result = roundtrip_validate(workflow, GET_TOOL_INFO, workflow_path="test_workflow_two_random_lines.ga")
        _assert_validation_ok(result)

    def test_workflow_batch(self):
        workflow = load_native_workflow("test_workflow_batch.ga")
        result = roundtrip_validate(workflow, GET_TOOL_INFO, workflow_path="test_workflow_batch.ga")
        _assert_validation_ok(result)

    def test_workflow_pause(self):
        workflow = load_native_workflow("test_workflow_pause.ga")
        result = roundtrip_validate(workflow, GET_TOOL_INFO, workflow_path="test_workflow_pause.ga")
        _assert_validation_ok(result)


class TestSubworkflowRoundTrip:
    """Test round-trip for workflows containing subworkflow steps."""

    def test_subworkflow_with_tags(self):
        workflow = load_native_workflow("test_subworkflow_with_tags.ga")
        result = roundtrip_validate(workflow, GET_TOOL_INFO, workflow_path="test_subworkflow_with_tags.ga")
        _assert_validation_ok(result)

    def test_subworkflow_with_integer_input(self):
        workflow = load_native_workflow("test_subworkflow_with_integer_input.ga")
        result = roundtrip_validate(workflow, GET_TOOL_INFO, workflow_path="test_subworkflow_with_integer_input.ga")
        _assert_validation_ok(result)


class TestFormat2RoundTrip:
    """Test round-trip for format2 workflows that we expect to work."""

    def test_simple_int(self):
        workflow = load_unit_workflow("valid/simple_int")
        native = python_to_workflow(workflow, galaxy_interface=None)
        result = roundtrip_native_workflow(native, GET_TOOL_INFO, "simple_int")
        _assert_roundtrip_passes(result)

    def test_simple_data(self):
        workflow = load_unit_workflow("valid/simple_data")
        native = python_to_workflow(workflow, galaxy_interface=None)
        result = roundtrip_native_workflow(native, GET_TOOL_INFO, "simple_data")
        _assert_roundtrip_passes(result)


class TestComparison:
    """Test the comparison logic itself."""

    def test_skip_bookkeeping_keys(self):
        orig = {"param": "5", "__current_case__": 0, "__page__": 0}
        after = {"param": 5}
        diffs = compare_tool_state(orig, after)
        assert len(diffs) == 0

    def test_type_coercion(self):
        assert _values_equivalent("5", 5)
        assert _values_equivalent(5, "5")
        assert _values_equivalent("3.14", 3.14)
        assert _values_equivalent("null", None)
        assert _values_equivalent(None, "null")
        assert not _values_equivalent("5", 6)

    def test_nested_comparison(self):
        orig = {"cond": {"selector": "a", "__current_case__": 0, "param": "1"}}
        after = {"cond": {"selector": "a", "param": 1}}
        diffs = compare_tool_state(orig, after)
        assert len(diffs) == 0

    def test_detects_mismatch(self):
        orig = {"param": "hello"}
        after = {"param": "world"}
        diffs = compare_tool_state(orig, after)
        assert len(diffs) == 1
        assert "param" in diffs[0]


def _assert_roundtrip_passes(result: RoundTripResult):
    failures = [r for r in result.step_results if not r.success]
    if failures:
        details = "\n".join(f"  step {f.step_id} ({f.tool_id}): [{f.failure_class}] {f.error}" for f in failures)
        pytest.fail(f"Round-trip failed for {result.workflow_name}:\n{details}")


def _assert_validation_ok(result: RoundTripValidationResult):
    if result.error:
        pytest.fail(f"Round-trip error for {result.workflow_path}: {result.error}")
    if result.conversion_result and not result.conversion_result.success:
        failures = [r for r in result.conversion_result.step_results if not r.success]
        details = "\n".join(f"  step {f.step_id} ({f.tool_id}): [{f.failure_class}] {f.error}" for f in failures)
        pytest.fail(f"Round-trip conversion failed for {result.workflow_path}:\n{details}")
    if result.diffs is None:
        pytest.fail(f"Full round-trip for {result.workflow_path} did not produce comparison")
    if result.diffs:
        details = "\n".join(f"  {d}" for d in result.diffs)
        pytest.fail(f"Round-trip diffs for {result.workflow_path}:\n{details}")


# -- IWC (ToolShed tool) workflows --

IWC_WORKFLOW_DIRECTORY = os.path.join(SCRIPT_DIRECTORY, "iwc")


def _iwc_workflows_available() -> list[str]:
    if not os.path.isdir(IWC_WORKFLOW_DIRECTORY):
        return []
    return sorted(f for f in os.listdir(IWC_WORKFLOW_DIRECTORY) if f.endswith(".ga"))


def _iwc_cache_populated(workflow_path: str) -> bool:
    from galaxy.tool_util.workflow_state.workflow_tools import extract_toolshed_tools

    with open(workflow_path) as f:
        workflow = json.load(f)
    tools = extract_toolshed_tools(workflow)
    if not tools:
        return True
    from galaxy.tool_util.workflow_state.toolshed_tool_info import ToolShedGetToolInfo

    tool_info = ToolShedGetToolInfo()
    return all(tool_info.has_cached(tid, tver) for tid, tver in tools)


def run_iwc_sweep() -> dict[str, RoundTripResult]:
    results: dict[str, RoundTripResult] = {}
    for filename in _iwc_workflows_available():
        path = os.path.join(IWC_WORKFLOW_DIRECTORY, filename)
        if not _iwc_cache_populated(path):
            results[f"iwc/{filename}"] = RoundTripResult(
                workflow_name=filename,
                direction="native_to_format2",
                step_results=[
                    StepResult(
                        step_id="cache",
                        tool_id=None,
                        success=False,
                        failure_class=FailureClass.TOOL_NOT_FOUND,
                        error="Cache not populated — run: galaxy-tool-cache populate-workflow " + path,
                    )
                ],
            )
            continue
        try:
            with open(path) as f:
                workflow = json.load(f)
            result = roundtrip_native_workflow(workflow, GET_TOOL_INFO_WITH_TOOLSHED, filename)
        except Exception as e:
            result = RoundTripResult(
                workflow_name=filename,
                direction="native_to_format2",
                step_results=[
                    StepResult(
                        step_id="load",
                        tool_id=None,
                        success=False,
                        failure_class=classify_error(e),
                        error=str(e),
                    )
                ],
            )
        results[f"iwc/{filename}"] = result
    return results


def run_iwc_full_roundtrip_sweep() -> dict[str, RoundTripValidationResult]:
    results: dict[str, RoundTripValidationResult] = {}
    for filename in _iwc_workflows_available():
        path = os.path.join(IWC_WORKFLOW_DIRECTORY, filename)
        if not _iwc_cache_populated(path):
            results[filename] = RoundTripValidationResult(
                workflow_path=filename,
                error="Cache not populated",
            )
            continue
        try:
            with open(path) as f:
                workflow = json.load(f)
            results[filename] = roundtrip_validate(workflow, GET_TOOL_INFO_WITH_TOOLSHED, workflow_path=filename)
        except Exception as e:
            results[filename] = RoundTripValidationResult(
                workflow_path=filename,
                error=str(e),
            )
    return results


class TestIWCRoundTrip:

    def test_iwc_sweep_report(self):
        workflows = _iwc_workflows_available()
        if not workflows:
            pytest.skip("No IWC workflows in test/unit/workflows/iwc/")

        results = run_iwc_sweep()
        print_sweep_results(results)

        total = len(results)
        passed = sum(1 for r in results.values() if r.success)
        failed = total - passed
        print(f"\nIWC sweep: {passed}/{total} passed, {failed} failed")

        failure_classes: dict[str, int] = {}
        for r in results.values():
            for sr in r.step_results:
                if not sr.success and sr.failure_class:
                    fc = sr.failure_class.value
                    failure_classes[fc] = failure_classes.get(fc, 0) + 1
        if failure_classes:
            print("Failure classes:")
            for fc, count in sorted(failure_classes.items()):
                print(f"  {fc}: {count}")

    def test_iwc_full_roundtrip_report(self):
        workflows = _iwc_workflows_available()
        if not workflows:
            pytest.skip("No IWC workflows in test/unit/workflows/iwc/")

        results = run_iwc_full_roundtrip_sweep()
        print_full_roundtrip_results(results)

        total = len(results)
        passed = sum(1 for r in results.values() if r.ok)
        print(f"\nIWC full round-trip: {passed}/{total} passed")


# -- CLI entry point --

if __name__ == "__main__":
    results = run_sweep()
    print_sweep_results(results)
