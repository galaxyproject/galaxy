"""Selenium tests that drive tool execution through the browser tool form,
reusing tool test definitions (XML <tests> blocks) for inputs and output
verification.
"""

import json
import os
import xml.etree.ElementTree as ET

import pytest

from galaxy.tool_util.loader_directory import looks_like_a_tool
from galaxy.tool_util.parser import get_tool_source
from galaxy.tool_util.toolbox.base import walk_tool_directories
from galaxy.util import string_as_bool
from galaxy.util.unittest_utils import skip_unless_environ
from galaxy_test.base.api import UsesCeleryTasks
from .framework import (
    managed_history,
    NavigatesGalaxyMixin,
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


def _add_tool_tests(pairs: set, path: str) -> None:
    """Record every (tool_id, test_index) pair a tool file declares."""
    if not os.path.exists(path):
        return
    try:
        tool_source = get_tool_source(path)
        tool_id = tool_source.parse_id()
        test_count = len(tool_source.parse_tests_to_dict()["tests"])
    except Exception:
        return
    if tool_id:
        pairs.update((tool_id, index) for index in range(test_count))


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
    pairs: set[tuple[str, int]] = set()
    root = ET.parse(FRAMEWORK_TOOL_CONF).getroot()
    for tool in root.iter("tool"):
        _add_tool_tests(pairs, os.path.join(FRAMEWORK_TOOLS_DIR, tool.get("file") or ""))
    # The panel also loads whole directories, which hold the typed parameter fixtures.
    for tool_dir in root.iter("tool_dir"):
        directory = os.path.join(FRAMEWORK_TOOLS_DIR, tool_dir.get("dir") or "")
        if not os.path.isdir(directory):
            continue
        for _, files in walk_tool_directories(directory, string_as_bool(tool_dir.get("recursive", True))):
            for path in files:
                # The directory also holds macros and option-generating scripts.
                if looks_like_a_tool(path, enable_beta_formats=True):
                    _add_tool_tests(pairs, path)
    return sorted(pairs)


FORM_ONLY_TOOL_TESTS = _framework_tool_tests()

# Tests the form-only pass cannot drive yet, with the reason for each. They still run;
# an entry that starts passing is reported as XPASS, which is the signal to delete it.
# Empty the dict to see the raw state of the suite.
KNOWN_FORM_FAILURES: dict[str, str] = {
    "async_conditional_no_default_nested_data_0": "the repeat renders one instance more than the test declares",
    "collection_split_on_column_0": "the staged datatype is not one the parameter accepts, so the form offers no dataset",
    "composite_pbed_0": "test data uses a datatype the instance does not know",
    "select_optional_0": "the search toggles fail the accessibility baseline this suite asserts",
    "select_optional_legacy_0": "the search toggles fail the accessibility baseline this suite asserts",
    "credentials_test_0": "the tool needs a credential this instance has none of",
    "credentials_test_1": "the tool needs a credential this instance has none of",
    "select_dynamic_0": "a select that renames its value column is filled from the wrong column",
    "filter_data_table_0": "options come from an unreachable from_url, so the tool does not load",
    "filter_data_table_1": "options come from an unreachable from_url, so the tool does not load",
    "filter_multiple_splitter_0": "options filtered on another parameter are absent from the default form, so the declared value cannot be mapped to its label",
    "filter_multiple_splitter_1": "options filtered on another parameter are absent from the default form, so the declared value cannot be mapped to its label",
    "filter_param_value_ref_attribute_2": "options filtered on another parameter are absent from the default form, so the declared value cannot be mapped to its label",
    "filter_param_value_ref_attribute_4": "options filtered on another parameter are absent from the default form, so the declared value cannot be mapped to its label",
    "format_source_in_conditional_1": "a data parameter two conditionals deep never becomes clickable",
    "implicit_conversion_optional_param_0": "test data uses a datatype the instance does not know",
    "inheritance_simple_0": "the staged datatype is not one the parameter accepts, so the form offers no dataset",
    "output_format_input_0": "the staged datatype is not one the parameter accepts, so the form offers no dataset",
    "select_from_dataset_1": "options read from a dataset are matched by position, not by value",
    "select_from_url_0": "no job appears after the form submits",
    "validation_hdf5_0": "the staged datatype is not one the parameter accepts, so the form offers no dataset",
    "gx_boolean_optional_checked_1": "a checked optional boolean cannot be returned to unset",
    "gx_drill_down_code_0": "the option element id is built from the option name, which the test declares by value",
    "gx_genomebuild_multiple_0": "only one of the declared builds reaches the request",
    "gx_genomebuild_multiple_1": "the search toggles fail the accessibility baseline this suite asserts",
    "gx_group_tag_0": "the harness does not stage a collection whose elements carry group tags",
    "gx_group_tag_multiple_0": "the harness does not stage a collection whose elements carry group tags",
    "gx_group_tag_multiple_1": "the harness does not stage a collection whose elements carry group tags",
    "gx_group_tag_optional_0": "the harness does not stage a collection whose elements carry group tags",
    "gx_group_tag_optional_1": "the harness does not stage a collection whose elements carry group tags",
    "gx_hidden_0": "a hidden parameter renders no control, so the declared value cannot be set in the browser",
    "gx_hidden_data_1": "a hidden parameter renders no control, so the declared value cannot be set in the browser",
    "gx_hidden_optional_0": "a hidden parameter renders no control, so the declared value cannot be set in the browser",
    "gx_repeat_select_dynamic_1": "a dynamic select inside a repeat never becomes clickable",
}


def _form_only_params():
    marked = []
    for tool_id, test_index in FORM_ONLY_TOOL_TESTS:
        test_key = f"{tool_id}_{test_index}"
        reason = KNOWN_FORM_FAILURES.get(test_key)
        marks = [pytest.mark.xfail(reason=reason, strict=False)] if reason else []
        marked.append(pytest.param(tool_id, test_index, marks=marks, id=test_key))
    return marked


# The selenium driver is configured once from SeleniumTestCase, so a per-class
# handle_galaxy_config_kwds never reaches the server. Set the overrides the config
# loader does read, and do it before the driver starts.
os.environ.setdefault("GALAXY_CONFIG_OVERRIDE_ENABLE_TOOL_REQUESTS", "true")
os.environ.setdefault("GALAXY_CONFIG_OVERRIDE_ENABLE_CELERY_TASKS", "true")


class AssertsAsyncSubmission(NavigatesGalaxyMixin):
    """Assert the browser submitted through the tool request API, not the legacy one."""

    def _assert_async_submission(self, tool_id, test_index, test_def=None):
        # Galaxy records the request before queueing the job, so this holds whatever the
        # tool goes on to do. Browser resource timings do not: they only show the tool
        # request polling a submission that succeeded.
        if (test_def or {}).get("expect_failure"):
            # An input set the test declares invalid is rejected before a request is
            # recorded, so there is nothing here to tell the two paths apart.
            return
        history_id = self.current_history_id()
        recorded = self.api_get(f"histories/{history_id}/tool_requests")
        assert recorded, f"{tool_id}[{test_index}] fell back to the legacy submission path"


@skip_unless_environ("GALAXY_TEST_E2E_TOOL_TESTS")
class TestToolFormHarness(AssertsAsyncSubmission, SeleniumTestCase, RunsToolTests, UsesCeleryTasks):
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
        self._assert_async_submission(tool_id, test_index, self.tool_test_def(tool_id, test_index, interactor))


@skip_unless_environ("GALAXY_TEST_E2E_TOOL_TESTS")
class TestToolFormOnlyHarness(AssertsAsyncSubmission, SeleniumTestCase, RunsToolTests, UsesCeleryTasks):
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
        self._assert_async_submission(tool_id, test_index, self.tool_test_def(tool_id, test_index, interactor))
