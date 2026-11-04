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
        gx_selenium_context.navigate_to_invocations_grid()
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

    @selenium_test
    def test_filter_by_workflow_and_history(self):
        first_history_id = self.dataset_populator.new_history()
        self.workflow_populator.run_workflow(
            WORKFLOW_RENAME_ON_INPUT,
            history_id=first_history_id,
            assert_ok=True,
            wait=True,
            invocations=2,
        )
        # run_workflow uploads the workflow again, so this is a second stored workflow
        second_history_id = self.dataset_populator.new_history()
        second_workflow_id = self.workflow_populator.run_workflow(
            WORKFLOW_RENAME_ON_INPUT,
            history_id=second_history_id,
            assert_ok=True,
            wait=True,
        ).workflow_id
        self.navigate_to_invocations_grid()
        invocations = self.components.invocations
        invocations.invocations_table.wait_for_visible()
        self._assert_showing_n_invocations(3)

        # newest first: row 0 is the second workflow's invocation
        invocations.invocations_table_cell_filter(row=0, column=1, key="workflow").wait_for_and_click()
        self._assert_showing_n_invocations(1)
        self._assert_filter_text(f"workflow:{second_workflow_id}")
        self.screenshot("invocations_filtered_by_workflow")

        self.published_grid_search_for(f"history:{first_history_id}")
        self._assert_showing_n_invocations(2)

        self.published_grid_search_for()
        self._assert_showing_n_invocations(3)
        invocations.invocations_table_cell_filter(row=2, column=2, key="history").wait_for_and_click()
        self._assert_showing_n_invocations(2)
        self._assert_filter_text(f"history:{first_history_id}")

    @retry_assertion_during_transitions
    def _assert_filter_text(self, expected):
        assert self.components.grids.free_text_search.wait_for_visible().get_attribute("value") == expected

    @retry_assertion_during_transitions
    def _assert_showing_n_invocations(self, n):
        assert len(self.invocation_index_table_elements()) == n
