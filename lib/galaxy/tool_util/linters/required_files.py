import fnmatch
import os
import re
from typing import TYPE_CHECKING

from galaxy.tool_util.lint import Linter

if TYPE_CHECKING:
    from galaxy.tool_util.lint import LintContext
    from galaxy.tool_util.parser import ToolSource

WALK_MAX_DIRS = 10000


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
            path = include["path"]
            path_type = include.get("path_type", "literal")
            if not _include_matches_files(include, tool_dir):
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
            else:
                if path_type == "literal":
                    lint_ctx.info(
                        f"Required file [{path}] found",
                        linter=cls.name(),
                    )
                else:
                    lint_ctx.info(
                        f"Required files pattern [{path}] (type {path_type}) matches files",
                        linter=cls.name(),
                    )


def _include_matches_files(include: dict, tool_dir: str) -> bool:
    """Check if an include pattern matches any files in the tool directory.

    Uses os.walk and direct file existence checks instead of
    RequiredFiles.find_required_files (which uses safe_walk), because
    safe_walk filters out files whose realpath resolves outside the tool
    directory. This causes false positives when linting tool directories
    containing symlinked files (e.g. planemo shed_lint realized repositories
    where files are symlinked into a temp directory).
    """
    path = include["path"]
    path_type = include.get("path_type", "literal")
    if path_type == "literal":
        return os.path.exists(os.path.join(tool_dir, path))
    for i, (dirpath, _, filenames) in enumerate(os.walk(tool_dir, followlinks=True)):
        if i >= WALK_MAX_DIRS:
            break
        for filename in filenames:
            rel_path = os.path.relpath(os.path.join(dirpath, filename), tool_dir)
            if path_type == "prefix":
                if rel_path.startswith(path):
                    return True
            elif path_type == "glob":
                if fnmatch.fnmatch(rel_path, path):
                    return True
            else:
                if re.match(path, rel_path) is not None:
                    return True
    return False