import os
from typing import TYPE_CHECKING

from galaxy.tool_util.lint import Linter
from galaxy.tool_util.parser.interface import RequiredFiles

if TYPE_CHECKING:
    from galaxy.tool_util.lint import LintContext
    from galaxy.tool_util.parser import ToolSource


class RequiredFilesExist(Linter):
    """Check that required_files include patterns match existing files."""

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        if not tool_source.source_path:
            return
        tool_dir = os.path.dirname(tool_source.source_path)
        required_files = tool_source.parse_required_files()
        if required_files is None:
            return
        for include in required_files.includes:
            per_include = RequiredFiles.from_dict(
                {
                    "includes": [include],
                    "excludes": [],
                    "extend_default_excludes": False,
                }
            )
            if not per_include.find_required_files(tool_dir):
                path = include["path"]
                path_type = include.get("path_type", "literal")
                if path_type == "literal":
                    lint_ctx.error(
                        f"Required file [{path}] does not exist",
                        linter=cls.name(),
                    )
                else:
                    lint_ctx.error(
                        f"Required files pattern [{path}] (type {path_type}) does not match any files",
                        linter=cls.name(),
                    )
