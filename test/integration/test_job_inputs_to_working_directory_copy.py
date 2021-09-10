"""Run various framework tool tests with inputs_to_working_directory = copy."""

from galaxy_test.driver import integration_util


class JobInputsToWorkingDirectoryCopyTestCase(integration_util.IntegrationInstance):
    """Describe a Galaxy test instance with inputs_to_working_directory enabled."""

    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["inputs_to_working_directory"] = 'copy'


instance = integration_util.integration_module_instance(JobInputsToWorkingDirectoryCopyTestCase)

test_tools = integration_util.integration_tool_runner(["output_format", "input_in_job_dir"])
