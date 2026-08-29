"""Selenium tests that drive tool execution through the browser tool form,
reusing tool test definitions (XML <tests> blocks) for inputs and output
verification.
"""

import json
import os
import xml.etree.ElementTree as ET

import pytest

from galaxy.tool_util.parser import get_tool_source

from galaxy.util.unittest_utils import skip_unless_environ
from galaxy_test.base.api import UsesCeleryTasks
from .framework import (
    managed_history,
    RunsToolTests,
    selenium_test,
    SeleniumTestCase,
)

DEFAULT_TOOL_TESTS = [
    ("environment_variables", 0),
    ("gx_int", 0),
    ("gx_float", 0),
    ("gx_text", 0),
    ("gx_select", 0),
    ("gx_boolean", 2),
    ("gx_color", 0),
    ("gx_int_optional", 0),
    ("gx_float_optional", 0),
    ("gx_text_optional", 0),
    ("gx_select_optional", 0),
    ("gx_select_multiple", 0),
    ("gx_boolean_optional", 3),
    ("gx_data", 0),
    ("gx_data_column", 0),
    ("data_optional", 0),
    ("multi_data_param", 0),
    ("gx_conditional_select", 1),
    ("gx_conditional_boolean", 2),
    ("gx_section_boolean", 0),
    ("implicit_default_conds", 0),
    ("boolean_conditional", 0),
    ("gx_repeat_boolean", 0),
    ("gx_repeat_data", 0),
    ("multi_repeats", 0),
    ("multi_repeats", 2),
    ("simple_constructs", 0),
    ("multi_output", 0),
    ("output_format", 0),
    ("output_filter", 0),
    ("column_param", 1),
    ("multi_select", 0),
    ("multi_select", 1),
    ("drill_down", 2),
    ("collection_paired_test", 0),
    ("collection_nested_test", 0),
    ("collection_nested_test", 1),
    ("collection_creates_list", 0),
    ("collection_mixed_param", 0),
    ("collection_optional_param", 1),
    ("collection_creates_pair", 0),
    ("collection_creates_list_of_pairs", 0),
    ("output_format_collection", 0),
    ("tool_directory", 0),
    ("from_work_dir_glob", 0),
    ("min_repeat", 0),
    ("implicit_conversion", 0),
    ("inheritance_simple", 1),
    ("markdown_report_simple", 0),
    ("gx_conditional_boolean_checked", 0),
    ("checksum", 0),
    ("qc_stdout", 0),
    ("cheetah_casting", 0),
    ("output_order", 0),
    ("output_filter", 2),
    ("cheetah_problem_unbound_var", 0),
    ("detect_errors", 1),
    ("cheetah_problem_syntax_error", 0),
    ("python_environment_problem", 0),
    ("output_filter_exception_1", 0),
    ("detect_errors", 0),
    ("sim_size_delta", 0),
    ("job_properties", 0),
    ("detect_errors_aggressive", 0),
    ("strict_shell", 0),
    ("strict_shell", 1),
    ("strict_shell_profile", 0),
    ("strict_shell_profile", 1),
    ("strict_shell_default_off", 0),
    ("unicode_stream", 0),
    ("unicode_stream", 1),
    ("unicode_stream", 2),
    ("multi_output_assign_primary", 0),
    ("multi_output_assign_primary_ext_dbkey", 0),
    ("tool_provided_metadata_2", 0),
    ("tool_provided_metadata_3", 0),
    ("tool_provided_metadata_6", 0),
    ("tool_provided_metadata_7", 0),
    ("tool_provided_metadata_10", 0),
]


def _tool_tests():
    """The (tool_id, test_index) pairs to drive.

    Defaults to the framework tools above. `GALAXY_TEST_TOOL_FORM_TESTS` overrides that with
    a JSON list of pairs, or a path to a file containing one, so an external caller can point
    the harness at its own tools -- shed tools installed elsewhere, for instance -- without
    editing this file.
    """
    spec = os.environ.get("GALAXY_TEST_TOOL_FORM_TESTS")
    if not spec:
        return DEFAULT_TOOL_TESTS
    if os.path.exists(spec):
        with open(spec) as fh:
            spec = fh.read()
    return [(str(tool_id), int(test_index)) for tool_id, test_index in json.loads(spec)]


TOOL_TESTS = _tool_tests()

FRAMEWORK_TOOLS_DIR = os.path.join(
    os.path.dirname(__file__), os.pardir, os.pardir, os.pardir, "test", "functional", "tools"
)
FRAMEWORK_TOOL_CONF = os.path.join(FRAMEWORK_TOOLS_DIR, "sample_tool_conf.xml")


def _framework_tool_tests():
    """Every (tool_id, test_index) pair in the framework tool suite.

    `GALAXY_TEST_TOOL_FORM_ONLY_TESTS` overrides it in the same JSON form as
    `GALAXY_TEST_TOOL_FORM_TESTS`, so the form-only pass can be aimed at shed tools.
    """
    spec = os.environ.get("GALAXY_TEST_TOOL_FORM_ONLY_TESTS")
    if spec:
        if os.path.exists(spec):
            with open(spec) as fh:
                spec = fh.read()
        return [(str(tool_id), int(test_index)) for tool_id, test_index in json.loads(spec)]
    # A tool can be listed more than once in the panel; test ids have to stay unique.
    pairs = set()
    for tool in ET.parse(FRAMEWORK_TOOL_CONF).getroot().iter("tool"):
        path = os.path.join(FRAMEWORK_TOOLS_DIR, tool.get("file") or "")
        if not os.path.exists(path):
            continue
        try:
            tool_source = get_tool_source(path)
            tool_id = tool_source.parse_id()
            test_count = len(tool_source.parse_tests_to_dict()["tests"])
        except Exception:
            continue
        if tool_id:
            pairs.update((tool_id, index) for index in range(test_count))
    return sorted(pairs)


FORM_ONLY_TOOL_TESTS = _framework_tool_tests()

# Tests the form-only pass cannot drive yet, with the reason for each. They still run;
# an entry that starts passing is reported as XPASS, which is the signal to delete it.
# Empty the dict to see the raw state of the suite.
KNOWN_FORM_FAILURES: dict[str, str] = {
    "filter_data_table_0": "options come from an unreachable from_url, so the tool does not load",
    "filter_data_table_1": "options come from an unreachable from_url, so the tool does not load",
    "dbkey_filter_multi_input_0": "select options arrive only after the data param round-trips",
    "dbkey_filter_multi_input_1": "select options arrive only after the data param round-trips",
    "dbkey_filter_multi_input_2": "select options arrive only after the data param round-trips",
    "select_from_dataset_0": "select options are read from a dataset chosen on the same form",
}


def _form_only_params():
    marked = []
    for tool_id, test_index in FORM_ONLY_TOOL_TESTS:
        test_key = f"{tool_id}_{test_index}"
        reason = KNOWN_FORM_FAILURES.get(test_key)
        marks = [pytest.mark.xfail(reason=reason, strict=False)] if reason else []
        marked.append(pytest.param(tool_id, test_index, marks=marks, id=test_key))
    return marked


@skip_unless_environ("GALAXY_TEST_E2E_TOOL_TESTS")
class TestToolFormHarness(SeleniumTestCase, RunsToolTests, UsesCeleryTasks):
    ensure_registered = True

    @selenium_test
    @managed_history
    @pytest.mark.parametrize("tool_id,test_index", TOOL_TESTS, ids=[f"{t[0]}_{t[1]}" for t in TOOL_TESTS])
    def test_tool(self, tool_id, test_index):
        interactor = self.api_interactor_for_logged_in_user()
        self.run_tool_test(
            tool_id,
            test_index=test_index,
            galaxy_interactor=interactor,
            dataset_populator=self.dataset_populator,
        )
        called = self.execute_script(
            "return performance.getEntriesByType('resource')"
            ".map(e => e.name).filter(n => n.includes('/api/tool_requests'));"
        )
        assert called, f"{tool_id}[{test_index}] fell back to the legacy submission path"


@skip_unless_environ("GALAXY_TEST_E2E_TOOL_TESTS")
class TestToolFormOnlyHarness(SeleniumTestCase, RunsToolTests):
    """Fill and submit every framework tool test without running the job."""

    ensure_registered = True

    @selenium_test
    @managed_history
    @pytest.mark.parametrize("tool_id,test_index", _form_only_params())
    def test_tool_form(self, tool_id, test_index):
        interactor = self.api_interactor_for_logged_in_user()
        self.run_tool_test(
            tool_id,
            test_index=test_index,
            galaxy_interactor=interactor,
            dataset_populator=self.dataset_populator,
            form_only=True,
        )
