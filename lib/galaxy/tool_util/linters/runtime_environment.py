"""Lint explicit runtime environment requirements of installed tools."""

import re

from galaxy.tool_util.lint import Linter

lint_tool_types = ["*"]


class RuntimeEnvironmentVariables(Linter):
    @classmethod
    def lint(cls, tool_source, lint_ctx):
        try:
            variables = tool_source.parse_runtime_environment_variables()
        except ValueError as exc:
            lint_ctx.error(str(exc), linter=cls.name())
            return
        if variables and tool_source.parse_class() == "GalaxyUserTool":
            lint_ctx.error("User-defined tools cannot declare runtime_environment_variable", linter=cls.name())
        for variable in variables:
            if re.search(r"SECRET|TOKEN|PASSWORD|API_KEY|^AWS_", variable.name, re.IGNORECASE):
                lint_ctx.warn(
                    f"Runtime environment variable {variable.name} looks like a secret; use <credentials> instead.",
                    linter=cls.name(),
                )
            if variable.description:
                lint_ctx.info(
                    f"Runtime environment variable {variable.name}: {variable.description}", linter=cls.name()
                )
