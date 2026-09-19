import os

from galaxy_test.base.decorators import requires_admin
from galaxy_test.base.populators import skip_without_tool
from galaxy_test.base.workflow_fixtures import (
    WORKFLOW_WITH_CUSTOM_REPORT_1,
    WORKFLOW_WITH_CUSTOM_REPORT_1_TEST_DATA,
)
from galaxy_test.selenium.framework import retry_assertion_during_transitions
from .framework import (
    selenium_test,
    SeleniumIntegrationTestCase,
)

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
JOB_CONFIG = os.path.join(SCRIPT_DIRECTORY, "test_admin_jobs_job_conf.yml")


class TestAdminJobsGrid(SeleniumIntegrationTestCase):
    run_as_admin = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["job_config_file"] = JOB_CONFIG

    @selenium_test
    @requires_admin
    @skip_without_tool("cat")
    def test_jobs_grid(self):
        admin_component = self.components.admin
        self.admin_login()
        with self.dataset_populator.test_history() as history_id:
            run_object = self.workflow_populator.run_workflow(
                WORKFLOW_WITH_CUSTOM_REPORT_1, test_data=WORKFLOW_WITH_CUSTOM_REPORT_1_TEST_DATA, history_id=history_id
            )
            self.workflow_populator.wait_for_invocation_and_jobs(
                history_id, run_object.workflow_id, run_object.invocation_id
            )
        self.admin_open()
        admin_component.index.jobs.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)
        manage_jobs = admin_component.manage_jobs
        manage_jobs.table.wait_for_visible()
        self.screenshot("admin_jobs_custom_configuration")
        self.sleep_for(self.wait_types.JOB_COMPLETION)
        assert len(manage_jobs.filter_link_by_tool(tool_id="cat").all()) == 2
        assert len(manage_jobs.filter_link_by_tool(tool_id="qc_stdout").all()) == 1
        self.assert_displays_at_least_n_rows(3)

        manage_jobs.filter_link_by_tool(tool_id="qc_stdout").wait_for_and_click()
        assert manage_jobs.filter_query.wait_for_value() == "tool:'qc_stdout'"
        self.assert_displays_n_rows(1)

        self.clear_index_filter()
        self.assert_displays_at_least_n_rows(3)

        manage_jobs.filter_link_by_runner(runner="local_cat").wait_for_and_click()
        self.assert_displays_n_rows(2)
        self.clear_index_filter()

    @retry_assertion_during_transitions
    @requires_admin
    def assert_displays_at_least_n_rows(self, n):
        admin_component = self.components.admin
        manage_jobs = admin_component.manage_jobs
        assert len(manage_jobs.filter_link_user.all()) >= n

    @retry_assertion_during_transitions
    @requires_admin
    def assert_displays_n_rows(self, n):
        admin_component = self.components.admin
        manage_jobs = admin_component.manage_jobs
        assert len(manage_jobs.filter_link_user.all()) == n

    @requires_admin
    def clear_index_filter(self):
        admin_component = self.components.admin
        manage_jobs = admin_component.manage_jobs
        # clear alone doesn't fire the debounce input...
        element = manage_jobs.filter_query.wait_for_visible()
        element.clear()
        element.send_keys("     ")
        self.send_enter(element)
