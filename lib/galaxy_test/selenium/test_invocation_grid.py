from galaxy_test.base.workflow_fixtures import WORKFLOW_RENAME_ON_INPUT
from .framework import (
    retry_assertion_during_transitions,
    selenium_test,
    SeleniumTestCase,
    TestsGalaxyPagers,
)


class TestInvocationGridSelenium(SeleniumTestCase, TestsGalaxyPagers):
    ensure_registered = True

    @selenium_test
    def test_grid(self):
        gx_selenium_context = self
        history_id = gx_selenium_context.dataset_populator.new_history()
        gx_selenium_context.workflow_populator.run_workflow(
            WORKFLOW_RENAME_ON_INPUT,
            history_id=history_id,
            assert_ok=True,
            wait=True,
            invocations=30,
        )
        gx_selenium_context.navigate_to_invocations()
        invocations = gx_selenium_context.components.invocations
        invocations.invocations_table.wait_for_visible()

        # shows a maximum of 25 invocations per page
        self._assert_showing_n_invocations(25)
        invocations.pager.wait_for_visible()
        self.screenshot("invocations_paginated_first_page")
        self._next_page(invocations)
        self._assert_current_page_is(invocations, 2)
        # shows the remaining 5 invocations on the second page
        self._assert_showing_n_invocations(5)
        self.screenshot("invocations_paginated_next_page")
        self._previous_page(invocations)
        self._assert_current_page_is(invocations, 1)
        self._last_page(invocations)
        self._assert_current_page_is(invocations, 2)
        self.screenshot("invocations_paginated_last_page")
        self._first_page(invocations)
        self._assert_current_page_is(invocations, 1)

    @retry_assertion_during_transitions
    def _assert_showing_n_invocations(self, n):
        assert len(self.invocation_index_table_elements()) == n
