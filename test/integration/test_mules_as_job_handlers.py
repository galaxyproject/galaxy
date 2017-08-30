"""Integration tests for job handlers as mules."""

import os

from base import integration_util

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))


class MulesAsJobHandlersIntegrationTestCase(integration_util.IntegrationTestCase):
    """Start uwsgi with mules and run a tool test."""

    framework_tool_and_types = True
    require_uwsgi = True

    @classmethod
    def handle_uwsgi_cli_command(cls, command):
        command.extend([
            "--mule=lib/galaxy/main.py",
            "--farm=job-handlers:1",
        ])

    def test_tool_simple_constructs(self):
        self._run_tool_test("simple_constructs")
