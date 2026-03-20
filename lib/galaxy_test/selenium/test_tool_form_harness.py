"""Selenium tests that drive tool execution through the browser tool form,
reusing tool test definitions (XML <tests> blocks) for inputs and output
verification.
"""

from galaxy.util.unittest_utils import skip_unless_environ
from .framework import (
    managed_history,
    RunsToolTests,
    selenium_test,
    SeleniumTestCase,
)


@skip_unless_environ("GALAXY_TEST_E2E_TOOL_TESTS")
class TestToolFormHarness(SeleniumTestCase, RunsToolTests):
    ensure_registered = True

    def _run(self, tool_id, test_index=0):
        interactor = self.api_interactor_for_logged_in_user()
        self.run_tool_test(
            tool_id,
            test_index=test_index,
            galaxy_interactor=interactor,
            dataset_populator=self.dataset_populator,
        )

    @selenium_test
    @managed_history
    def test_environment_variables(self):
        self._run("environment_variables", test_index=0)

    @selenium_test
    @managed_history
    def test_gx_float(self):
        self._run("gx_float", test_index=0)

    @selenium_test
    @managed_history
    def test_gx_select(self):
        self._run("gx_select", test_index=0)

    @selenium_test
    @managed_history
    def test_gx_boolean(self):
        self._run("gx_boolean", test_index=2)

    @selenium_test
    @managed_history
    def test_gx_conditional_select(self):
        self._run("gx_conditional_select", test_index=1)

    @selenium_test
    @managed_history
    def test_gx_section_boolean(self):
        self._run("gx_section_boolean", test_index=0)

    @selenium_test
    @managed_history
    def test_gx_data(self):
        self._run("gx_data", test_index=0)

    @selenium_test
    @managed_history
    def test_gx_repeat_boolean(self):
        self._run("gx_repeat_boolean", test_index=0)

    @selenium_test
    @managed_history
    def test_gx_color(self):
        self._run("gx_color", test_index=0)

    @selenium_test
    @managed_history
    def test_simple_constructs(self):
        self._run("simple_constructs", test_index=0)

    @selenium_test
    @managed_history
    def test_gx_conditional_boolean(self):
        self._run("gx_conditional_boolean", test_index=2)

    @selenium_test
    @managed_history
    def test_multi_output(self):
        self._run("multi_output", test_index=0)

    @selenium_test
    @managed_history
    def test_data_optional(self):
        self._run("data_optional", test_index=0)

    @selenium_test
    @managed_history
    def test_implicit_default_conds(self):
        self._run("implicit_default_conds", test_index=0)

    @selenium_test
    @managed_history
    def test_column_param(self):
        self._run("column_param", test_index=1)

    @selenium_test
    @managed_history
    def test_multi_repeats(self):
        self._run("multi_repeats", test_index=0)

    @selenium_test
    @managed_history
    def test_gx_repeat_data(self):
        self._run("gx_repeat_data", test_index=0)

    @selenium_test
    @managed_history
    def test_multi_select(self):
        self._run("multi_select", test_index=1)

    @selenium_test
    @managed_history
    def test_multi_select_multiple(self):
        self._run("multi_select", test_index=0)

    @selenium_test
    @managed_history
    def test_drill_down(self):
        self._run("drill_down", test_index=2)

    @selenium_test
    @managed_history
    def test_multi_data_param(self):
        self._run("multi_data_param", test_index=0)

    @selenium_test
    @managed_history
    def test_collection_paired(self):
        self._run("collection_paired_test", test_index=0)

    @selenium_test
    @managed_history
    def test_collection_nested(self):
        self._run("collection_nested_test", test_index=0)

    @selenium_test
    @managed_history
    def test_collection_nested_paired(self):
        self._run("collection_nested_test", test_index=1)

    @selenium_test
    @managed_history
    def test_collection_list(self):
        self._run("collection_creates_list", test_index=0)

    @selenium_test
    @managed_history
    def test_collection_mixed_param(self):
        self._run("collection_mixed_param", test_index=0)

    @selenium_test
    @managed_history
    def test_collection_optional_absent(self):
        self._run("collection_optional_param", test_index=1)

    @selenium_test
    @managed_history
    def test_collection_creates_pair(self):
        self._run("collection_creates_pair", test_index=0)

    @selenium_test
    @managed_history
    def test_collection_creates_list_of_pairs(self):
        self._run("collection_creates_list_of_pairs", test_index=0)
