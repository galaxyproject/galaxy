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
        workflow_name = self._get_random_name(prefix="filter workflow ")
        history_name = self._get_random_name(prefix="filter history ")
        first_history_id = self.dataset_populator.new_history()
        first_workflow_id = self.workflow_populator.run_workflow(
            WORKFLOW_RENAME_ON_INPUT,
            history_id=first_history_id,
            assert_ok=True,
            wait=True,
            invocations=2,
        ).workflow_id
        # run_workflow uploads the workflow again, so this is a second stored workflow
        second_history_id = self.dataset_populator.new_history(name=history_name)
        second_workflow_id = self.workflow_populator.run_workflow(
            WORKFLOW_RENAME_ON_INPUT,
            history_id=second_history_id,
            assert_ok=True,
            wait=True,
        ).workflow_id
        # both workflows share a name, like a workflow imported twice
        for workflow_id in (first_workflow_id, second_workflow_id):
            self.workflow_populator.update_workflow_fields(workflow_id, {"name": workflow_name}).raise_for_status()
        # keeps its own name, so the name and history filters have a run to exclude
        self.workflow_populator.run_workflow(
            WORKFLOW_RENAME_ON_INPUT,
            history_id=first_history_id,
            assert_ok=True,
            wait=True,
        )
        self.navigate_to_invocations_grid()
        invocations = self.components.invocations
        invocations.invocations_table.wait_for_visible()
        self._assert_showing_n_invocations(4)

        invocations.column_filter_toggle(key="workflow_id").wait_for_and_click()
        self._assert_n_elements(invocations.column_filter_options(key="workflow_id"), 3)
        invocations.column_filter_search(key="workflow_id").wait_for_and_send_keys(workflow_name)
        self._assert_n_elements(invocations.column_filter_options(key="workflow_id"), 2)
        invocations.column_filter_option(key="workflow_id", id=second_workflow_id).wait_for_and_click()
        self._assert_showing_n_invocations(1)
        self._assert_filter_text(f"workflow_id:{second_workflow_id}")
        invocations.column_filter_option(key="workflow_id", id=first_workflow_id).wait_for_and_click()
        self._assert_showing_n_invocations(3)
        self._assert_n_elements(invocations.active_column_filters(key="workflow_id"), 2)
        self.screenshot("invocations_column_filter_workflows")

        invocations.active_column_filter(key="workflow_id", id=second_workflow_id).wait_for_and_click()
        self._assert_showing_n_invocations(2)
        self._assert_filter_text(f"workflow_id:{first_workflow_id}")
        invocations.active_column_filter(key="workflow_id", id=first_workflow_id).wait_for_and_click()
        self._assert_showing_n_invocations(4)

        invocations.column_filter_toggle(key="history_id").wait_for_and_click()
        invocations.column_filter_search(key="history_id").wait_for_and_send_keys(history_name)
        self._assert_n_elements(invocations.column_filter_options(key="history_id"), 1)
        invocations.column_filter_option(key="history_id", id=second_history_id).wait_for_and_click()
        self._assert_showing_n_invocations(1)
        self._assert_n_elements(invocations.active_column_filters(key="history_id"), 1)

        self.published_grid_search_for(f"workflow:'{workflow_name}'")
        self._assert_showing_n_invocations(3)
        self._assert_n_elements(invocations.active_column_filters(key="history_id"), 0)

        # picking in a column removes the name filter of that kind
        invocations.column_filter_toggle(key="workflow_id").wait_for_and_click()
        invocations.column_filter_option(key="workflow_id", id=first_workflow_id).wait_for_and_click()
        self._assert_showing_n_invocations(2)
        self._assert_filter_text(f"workflow_id:{first_workflow_id}")

        # column filters stay available when nothing matches
        self.published_grid_search_for("workflow:no-such-workflow")
        self._assert_showing_n_invocations(0)
        invocations.column_filter_toggle(key="workflow_id").wait_for_visible()

    @retry_assertion_during_transitions
    def _assert_n_elements(self, component, n):
        assert len(component.all()) == n

    @retry_assertion_during_transitions
    def _assert_filter_text(self, expected):
        assert self.components.grids.free_text_search.wait_for_visible().get_attribute("value") == expected

    @retry_assertion_during_transitions
    def _assert_showing_n_invocations(self, n):
        assert len(self.invocation_index_table_elements()) == n
