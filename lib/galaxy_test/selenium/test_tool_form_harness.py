"""Selenium tests that drive tool execution through the browser tool form,
reusing tool test definitions (XML <tests> blocks) for inputs and output
verification.
"""

import pytest

from galaxy.util.unittest_utils import skip_unless_environ
from .framework import (
    managed_history,
    RunsToolTests,
    selenium_test,
    SeleniumTestCase,
)

TOOL_TESTS = [
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


@skip_unless_environ("GALAXY_TEST_E2E_TOOL_TESTS")
class TestToolFormHarness(SeleniumTestCase, RunsToolTests):
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
