"""Integration tests for the Pulsar embedded runner."""

from galaxy_test.driver import integration_util


class ToolTestIntegrationInstance(integration_util.IntegrationInstance):
    """Describe a Galaxy test instance with embedded pulsar configured."""

    framework_tool_and_types = True

instance = integration_util.integration_module_instance(ToolTestIntegrationInstance)

test_tools = integration_util.integration_tool_runner(['multiple_versions'], tool_version='0.1')
