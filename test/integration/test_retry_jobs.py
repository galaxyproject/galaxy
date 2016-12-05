"""Integration tests for the Pulsar embedded runner."""

import os

from base import integration_util

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
JOB_RETRY_JOB_CONFIG_FILE = os.path.join(SCRIPT_DIRECTORY, "retry_jobs_job_conf.xml")
JOB_RETRY_JOB_RESOURCES_CONFIG_FILE = os.path.join(SCRIPT_DIRECTORY, "retry_jobs_job_resource_parameters_conf.xml")


class RetryJobsIntegrationTestCase(integration_util.IntegrationTestCase):

    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["job_config_file"] = JOB_RETRY_JOB_CONFIG_FILE
        config["job_resource_params_file"] = JOB_RETRY_JOB_RESOURCES_CONFIG_FILE

    def test_retry_tools_have_resource_params(self):
        tool_show = self._get("tools/simple_constructs", data=dict(io_details=True)).json()
        tool_inputs = tool_show["inputs"]
        input_names = map(lambda x: x["name"], tool_inputs)
        assert "__job_resource" in input_names

    def test_job_resources(self):
        """If the test name comes through okay - we know that resource parameters are being propagated and dynamic jobs are working."""
        self._run_tool_test("simple_constructs", resource_parameters={"test_name": "test_job_resources"})

    def test_walltime_resubmission(self):
        exception_thrown = False
        try:
            self._run_tool_test("simple_constructs", resource_parameters={"test_name": "test_walltime_resubmission"})
        except Exception:
            exception_thrown = True

        assert not exception_thrown

    def test_memory_resubmission(self):
        exception_thrown = False
        try:
            self._run_tool_test("simple_constructs", resource_parameters={"test_name": "test_memory_resubmission"})
        except Exception:
            exception_thrown = True

        assert not exception_thrown
