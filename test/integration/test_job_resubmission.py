"""Integration tests for the job resubmission."""

import os

from galaxy_test.driver import integration_util
from galaxy_test.base.populators import DatasetPopulator

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
JOB_RESUBMISSION_JOB_CONFIG_FILE = os.path.join(SCRIPT_DIRECTORY, "resubmission_job_conf.yml")
JOB_RESUBMISSION_DEFAULT_JOB_CONFIG_FILE = os.path.join(SCRIPT_DIRECTORY, "resubmission_default_job_conf.xml")
JOB_RESUBMISSION_DYNAMIC_JOB_CONFIG_FILE = os.path.join(SCRIPT_DIRECTORY, "resubmission_dynamic_job_conf.xml")
JOB_RESUBMISSION_SMALL_MEMORY_JOB_CONFIG_FILE = os.path.join(SCRIPT_DIRECTORY, "resubmission_small_memory_job_conf.xml")
JOB_RESUBMISSION_SMALL_MEMORY_RESUBMISSION_TO_LARGE_JOB_CONFIG_FILE = os.path.join(
    SCRIPT_DIRECTORY, "resubmission_small_memory_resubmission_to_large_job_conf.xml"
)
JOB_RESUBMISSION_TOOL_DETECTED_ALWAYS_ERROR_JOB_CONFIG_FILE = os.path.join(
    SCRIPT_DIRECTORY, "resubmission_tool_detected_always_error_job_conf.xml"
)
JOB_RESUBMISSION_TOOL_DETECTED_RESUBMIT_JOB_CONFIG_FILE = os.path.join(
    SCRIPT_DIRECTORY, "resubmission_tool_detected_resubmit_job_conf.xml"
)
JOB_RESUBMISSION_JOB_RESOURCES_CONFIG_FILE = os.path.join(
    SCRIPT_DIRECTORY, "resubmission_job_resource_parameters_conf.xml"
)
JOB_RESUBMISSION_PULSAR_JOB_CONFIG_FILE = os.path.join(SCRIPT_DIRECTORY, "resubmission_pulsar_job_conf.xml")


class _BaseResubmissionIntegrationTestCase(integration_util.IntegrationTestCase):
    framework_tool_and_types = True

    def _assert_job_passes(self, tool_id="exit_code_oom", resource_parameters=None, history_id=None):
        resource_parameters = resource_parameters or {}
        self._run_tool_test(tool_id, resource_parameters=resource_parameters, test_history=history_id)

    def _assert_job_fails(self, tool_id="exit_code_oom", resource_parameters=None, history_id=None):
        resource_parameters = resource_parameters or {}
        exception_thrown = False
        try:
            self._run_tool_test(tool_id, resource_parameters=resource_parameters, test_history=history_id)
        except Exception:
            exception_thrown = True

        assert exception_thrown


class TestJobResubmissionIntegration(_BaseResubmissionIntegrationTestCase):
    framework_tool_and_types = True
    dataset_populator: DatasetPopulator

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["job_config_file"] = JOB_RESUBMISSION_JOB_CONFIG_FILE
        config["job_resource_params_file"] = JOB_RESUBMISSION_JOB_RESOURCES_CONFIG_FILE
        config["job_runner_monitor_sleep"] = 1
        config["job_handler_monitor_sleep"] = 1
        config["job_metrics"] = [{"type": "core"}]
        # Can't set job_metrics_config_file to None as default location will be used otherwise
        config["job_metrics_config_file"] = "xxx.xml"

    def test_retry_tools_have_resource_params(self):
        tool_show = self._get("tools/simple_constructs", data=dict(io_details=True)).json()
        tool_inputs = tool_show["inputs"]
        input_names = (x["name"] for x in tool_inputs)
        assert "__job_resource" in input_names

    def test_job_resources(self):
        """Test initial environment dynamic rule used by remaining re-submission test case works."""
        self._assert_job_passes(
            resource_parameters={"test_name": "test_job_resources", "initial_target_environment": "local"}
        )

    def test_failure_runner(self):
        """Test FailsJobRunner used by remaining re-submission test cases."""
        self._assert_job_fails(
            resource_parameters={
                "test_name": "test_failure_runner",
                "initial_target_environment": "fails_without_resubmission",
            }
        )

    def test_failure_runner_job_metrics_collected(self):
        with self.dataset_populator.test_history() as history_id:
            self._assert_job_fails(
                resource_parameters={
                    "test_name": "test_failure_runner",
                    "initial_target_environment": "fails_without_resubmission",
                },
                history_id=history_id,
            )
            jobs = self.dataset_populator.history_jobs(history_id=history_id)
            assert len(jobs) == 1
            job_metrics = self.dataset_populator._get(f"/api/jobs/{jobs[0]['id']}/metrics").json()
            assert job_metrics

    def test_walltime_resubmission(self):
        self._assert_job_passes(
            resource_parameters={"test_name": "test_walltime_resubmission", "failure_state": "walltime_reached"}
        )

    def test_memory_resubmission(self):
        self._assert_job_passes(
            resource_parameters={"test_name": "test_memory_resubmission", "failure_state": "memory_limit_reached"}
        )

    def test_unknown_error(self):
        self._assert_job_passes(
            resource_parameters={"test_name": "test_unknown_error", "failure_state": "unknown_error"}
        )

    def test_condition_expressions(self):
        self._assert_job_passes(
            resource_parameters={
                "test_name": "test_condition_expressions_0",
                "initial_target_environment": "fail_first_if_memory_or_walltime",
                "failure_state": "memory_limit_reached",
            }
        )
        self._assert_job_passes(
            resource_parameters={
                "test_name": "test_condition_expressions_1",
                "initial_target_environment": "fail_first_if_memory_or_walltime",
                "failure_state": "walltime_reached",
            }
        )
        self._assert_job_fails(
            resource_parameters={
                "test_name": "test_condition_expressions_2",
                "initial_target_environment": "fail_first_if_memory_or_walltime",
                "failure_state": "unknown_error",
            }
        )

    def test_condition_any_failure(self):
        self._assert_job_passes(
            resource_parameters={
                "test_name": "test_condition_any_failure",
                "initial_target_environment": "fail_first_any_failure",
                "failure_state": "unknown_error",
            }
        )

    def test_condition_attempt(self):
        self._assert_job_fails(
            resource_parameters={
                "test_name": "test_condition_attempt",
                "initial_target_environment": "fail_two_attempts",
                "failure_state": "unknown_error",
            }
        )
        self._assert_job_passes(
            resource_parameters={
                "test_name": "test_condition_attempt",
                "initial_target_environment": "fail_two_attempts",
                "failure_state": "walltime_reached",
            }
        )

    def test_condition_seconds_running(self):
        self._assert_job_passes(
            resource_parameters={
                "test_name": "test_condition_seconds_running",
                "initial_target_environment": "resubmit_if_short",
                "failure_state": "walltime_reached",
                "run_for": "1",
            }
        )
        self._assert_job_fails(
            resource_parameters={
                "test_name": "test_condition_seconds_running",
                "initial_target_environment": "resubmit_if_short",
                "failure_state": "walltime_reached",
                "run_for": "15",
            }
        )

    def test_resubmission_after_delay(self):
        self._assert_job_passes(
            resource_parameters={
                "test_name": "test_resubmission_after_delay",
                "initial_target_environment": "resubmit_after_delay",
                "failure_state": "unknown_error",
            }
        )

    def test_resubmission_after_delay_expression(self):
        self._assert_job_passes(
            resource_parameters={
                "test_name": "test_resubmission_after_delay_expression",
                "initial_target_environment": "resubmit_after_two_delays",
                "failure_state": "unknown_error",
            }
        )


class TestJobResubmissionDefaultIntegration(_BaseResubmissionIntegrationTestCase):
    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["default_job_resubmission_condition"] = "attempt < 2"
        config["job_config_file"] = JOB_RESUBMISSION_DEFAULT_JOB_CONFIG_FILE
        config["job_resource_params_file"] = JOB_RESUBMISSION_JOB_RESOURCES_CONFIG_FILE

    def test_default_resubmission(self):
        self._assert_job_passes(resource_parameters={"test_name": "test_default_resubmission"})


class TestJobResubmissionDynamicIntegration(_BaseResubmissionIntegrationTestCase):
    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["job_config_file"] = JOB_RESUBMISSION_DYNAMIC_JOB_CONFIG_FILE

    def test_dynamic_resubmission(self):
        self._assert_job_passes()


# Verify the test tool fails if only a small amount of memory is allocated.
class TestJobResubmissionSmallMemoryIntegration(_BaseResubmissionIntegrationTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["job_config_file"] = JOB_RESUBMISSION_SMALL_MEMORY_JOB_CONFIG_FILE

    def test_dynamic_resubmission(self):
        self._assert_job_fails()


# Verify the test tool will resubmit on failure tested above and will then pass with
# proper resubmission condition.
class TestJobResubmissionSmallMemoryResubmitsToLargeIntegration(_BaseResubmissionIntegrationTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["job_config_file"] = JOB_RESUBMISSION_SMALL_MEMORY_RESUBMISSION_TO_LARGE_JOB_CONFIG_FILE

    def test_dynamic_resubmission(self):
        self._assert_job_passes()


# Verify the test tool fails with an exit code issue.
class TestJobResubmissionToolDetectedErrorIntegration(_BaseResubmissionIntegrationTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["job_config_file"] = JOB_RESUBMISSION_TOOL_DETECTED_ALWAYS_ERROR_JOB_CONFIG_FILE

    def test_dynamic_resubmission(self):
        self._assert_job_fails(tool_id="exit_code_from_env")


# Verify the test tool will resubmit on failure tested above and will then pass in
# an environment without a tool indicated error.
class TestJobResubmissionToolDetectedErrorResubmitsIntegration(_BaseResubmissionIntegrationTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["job_config_file"] = JOB_RESUBMISSION_TOOL_DETECTED_RESUBMIT_JOB_CONFIG_FILE

    def test_dynamic_resubmission(self):
        self._assert_job_passes(tool_id="exit_code_from_env")


# Verify that a failure to connect to pulsar can trigger a resubmit
class TestJobResubmissionPulsarIntegration(_BaseResubmissionIntegrationTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["job_config_file"] = JOB_RESUBMISSION_PULSAR_JOB_CONFIG_FILE

    def test_resubmit_on_invalid_pulsar_url(self):
        self._assert_job_passes()
