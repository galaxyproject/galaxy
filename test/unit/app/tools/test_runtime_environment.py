from unittest import mock

import pytest

from galaxy.app_unittest_utils import tools_support
from galaxy.tool_util.parser.yaml import (
    UntrustedToolSourceError,
    YamlToolSource,
)
from galaxy.tool_util_models.runtime_environment import RuntimeEnvironmentVariable
from galaxy.tools import create_tool_from_source
from galaxy.util.unittest import TestCase

USER_TOOL = {
    "class": "GalaxyUserTool",
    "id": "runtime",
    "name": "Runtime",
    "version": "1.0",
    "container": "busybox",
    "shell_command": "true",
    "inputs": [],
    "outputs": [],
}


class TestRuntimeEnvironment(TestCase, tools_support.UsesTools):
    def setUp(self):
        self.setup_app()

    def tearDown(self):
        self.tear_down_app()

    def test_yaml_parser_rejects_user_runtime_declarations(self):
        with pytest.raises(UntrustedToolSourceError, match="runtime_environment_variables"):
            YamlToolSource({**USER_TOOL, "runtime_environment_variables": [{"name": "LICENSE_SERVER"}]})

    def test_tool_parse_rejects_user_runtime_declarations(self):
        source = YamlToolSource(USER_TOOL)
        # Exercise Tool's defense even if another ToolSource supplies declarations.
        with mock.patch.object(
            source,
            "parse_runtime_environment_variables",
            return_value=[RuntimeEnvironmentVariable(name="LICENSE_SERVER")],
        ):
            with pytest.raises(ValueError, match="User-defined tools cannot declare"):
                create_tool_from_source(self.app, source)

    @pytest.mark.parametrize("fmt", ["xml", "yaml"])
    def test_installed_tool_skips_bad_runtime_declaration(self, fmt):
        if fmt == "xml":
            tool = self._init_tool(
                '<tool id="runtime" name="Runtime" version="1.0"><requirements>'
                '<runtime_environment_variable name="PATH"/><runtime_environment_variable name="LICENSE_SERVER"/>'
                "</requirements><command>true</command><inputs/><outputs/></tool>"
            )
        else:
            source = YamlToolSource(
                {
                    **USER_TOOL,
                    "class": "GalaxyTool",
                    "runtime_environment_variables": [{"name": "PATH"}, {"name": "LICENSE_SERVER"}],
                }
            )
            tool = create_tool_from_source(self.app, source)
        assert [variable.name for variable in tool.runtime_environment_variables] == ["LICENSE_SERVER"]
