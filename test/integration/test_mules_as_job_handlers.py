"""Integration tests for job handlers as mules."""

import os

from base import integration_util
from base.populators import DatasetPopulator

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))


class _BaseMulesIntegrationTestCase(integration_util.IntegrationTestCase):
    """Start uwsgi with mules and run a tool test."""

    framework_tool_and_types = True
    require_uwsgi = True
    expected_server_name = 'main.web'

    def test_runs_on_mule(self):
        tool_id = 'config_vars'
        expect_server_name = self.expected_server_name
        dataset_populator = DatasetPopulator(self.galaxy_interactor)
        history_id = dataset_populator.new_history()
        payload = dataset_populator.run_tool(
            tool_id=tool_id,
            inputs={'var': 'server_name'},
            history_id=history_id,
        )
        dataset_id = payload['outputs'][0]['id']
        dataset_populator.wait_for_dataset(history_id, dataset_id, assert_ok=True)
        output = dataset_populator.get_history_dataset_content(history_id, dataset_id=dataset_id).strip()
        assert output.startswith(expect_server_name), (
            "Job handler's server name '{output}' does not start with expected string '{expected}'".format(
                output=output,
                expected=expect_server_name,
            )
        )


class SingleMuleAsJobHandlersIntegrationTestCase(_BaseMulesIntegrationTestCase):

    expected_server_name = 'main.job-handlers'

    @classmethod
    def handle_uwsgi_cli_command(cls, command):
        command.extend([
            "--py-call-osafterfork",
            "--mule=lib/galaxy/main.py",
            "--farm=job-handlers:1",
        ])


class MultipleMulesAsJobHandlersIntegrationTestCase(_BaseMulesIntegrationTestCase):

    expected_server_name = 'main.job-handlers'

    @classmethod
    def handle_uwsgi_cli_command(cls, command):
        command.extend([
            "--py-call-osafterfork",
            "--mule=lib/galaxy/main.py",
            "--mule=lib/galaxy/main.py",
            "--farm=job-handlers:1,2",
        ])
