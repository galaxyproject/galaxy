"""Integration tests for the Pulsar embedded runner."""

import os

from base import integration_util

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
JOB_RESUBMISSION_JOB_CONFIG_FILE = os.path.join(SCRIPT_DIRECTORY, "resubmission_job_conf.xml")
JOB_RESUBMISSION_DEFAULT_JOB_CONFIG_FILE = os.path.join(SCRIPT_DIRECTORY, "resubmission_default_job_conf.xml")
JOB_RESUBMISSION_JOB_RESOURCES_CONFIG_FILE = os.path.join(SCRIPT_DIRECTORY, "resubmission_job_resource_parameters_conf.xml")


class _BaseResubmissionIntegerationTestCase(integration_util.IntegrationTestCase):
    framework_tool_and_types = True

    def _assert_job_passes(self, resource_parameters):
        self._run_tool_test("simple_constructs", resource_parameters=resource_parameters)

    def _assert_job_fails(self, resource_parameters):
        exception_thrown = False
        try:
            self._run_tool_test("simple_constructs", resource_parameters=resource_parameters)
        except Exception:
            exception_thrown = True

        assert exception_thrown


class JobResubmissionIntegrationTestCase(_BaseResubmissionIntegerationTestCase):

    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["job_config_file"] = JOB_RESUBMISSION_JOB_CONFIG_FILE
        config["job_resource_params_file"] = JOB_RESUBMISSION_JOB_RESOURCES_CONFIG_FILE

    def test_retry_tools_have_resource_params(self):
        tool_show = self._get("tools/simple_constructs", data=dict(io_details=True)).json()
        tool_inputs = tool_show["inputs"]
        input_names = map(lambda x: x["name"], tool_inputs)
        assert "__job_resource" in input_names

    def test_job_resources(self):
        """Test initial destination dynamic rule used by remaining re-submission test case works."""
        self._assert_job_passes(resource_parameters={"test_name": "test_job_resources", "initial_destination": "local"})

    def test_failure_runner(self):
        """Test FailsJobRunner used by remaining re-submission test cases."""
        self._assert_job_fails(resource_parameters={"test_name": "test_failure_runner", "initial_destination": "fails_without_resubmission"})

    def test_walltime_resubmission(self):
        self._assert_job_passes(resource_parameters={"test_name": "test_walltime_resubmission", "failure_state": "walltime_reached"})

    def test_memory_resubmission(self):
        self._assert_job_passes(resource_parameters={"test_name": "test_memory_resubmission", "failure_state": "memory_limit_reached"})

    def test_unknown_error(self):
        self._assert_job_passes(resource_parameters={"test_name": "test_unknown_error", "failure_state": "unknown_error"})

    def test_condition_expressions(self):
        self._assert_job_passes(resource_parameters={"test_name": "test_condition_expressions_0",
                                                     "initial_destination": "fail_first_if_memory_or_walltime",
                                                     "failure_state": "memory_limit_reached"})
        self._assert_job_passes(resource_parameters={"test_name": "test_condition_expressions_1",
                                                     "initial_destination": "fail_first_if_memory_or_walltime",
                                                     "failure_state": "walltime_reached"})
        self._assert_job_fails(resource_parameters={"test_name": "test_condition_expressions_2",
                                                    "initial_destination": "fail_first_if_memory_or_walltime",
                                                    "failure_state": "unknown_error"})

    def test_condition_any_failure(self):
        self._assert_job_passes(resource_parameters={"test_name": "test_condition_any_failure",
                                                     "initial_destination": "fail_first_any_failure",
                                                     "failure_state": "unknown_error"})

    def test_condition_attempt(self):
        self._assert_job_fails(resource_parameters={"test_name": "test_condition_attempt",
                                                    "initial_destination": "fail_two_attempts",
                                                    "failure_state": "unknown_error"})
        self._assert_job_passes(resource_parameters={"test_name": "test_condition_attempt",
                                                     "initial_destination": "fail_two_attempts",
                                                     "failure_state": "walltime_reached"})

    def test_condition_seconds_running(self):
        self._assert_job_passes(resource_parameters={"test_name": "test_condition_seconds_running",
                                                     "initial_destination": "resubmit_if_short",
                                                     "failure_state": "walltime_reached",
                                                     "run_for": "1"})
        self._assert_job_fails(resource_parameters={"test_name": "test_condition_seconds_running",
                                                    "initial_destination": "resubmit_if_short",
                                                    "failure_state": "walltime_reached",
                                                    "run_for": "15"})

    def test_resubmission_after_delay(self):
        self._assert_job_passes(resource_parameters={"test_name": "test_resubmission_after_delay",
                                                     "initial_destination": "resubmit_after_delay",
                                                     "failure_state": "unknown_error"})

    def test_resubmission_after_delay_expression(self):
        self._assert_job_passes(resource_parameters={"test_name": "test_resubmission_after_delay_expression",
                                                     "initial_destination": "resubmit_after_two_delays",
                                                     "failure_state": "unknown_error"})


class JobResubmissionDefaultIntegrationTestCase(_BaseResubmissionIntegerationTestCase):

    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["default_job_resubmission_condition"] = "attempt < 2"
        config["job_config_file"] = JOB_RESUBMISSION_DEFAULT_JOB_CONFIG_FILE
        config["job_resource_params_file"] = JOB_RESUBMISSION_JOB_RESOURCES_CONFIG_FILE

    def test_default_resubmission(self):
        self._assert_job_passes(resource_parameters={"test_name": "test_default_resubmission"})
