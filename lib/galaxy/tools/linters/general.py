"""This module contains a linting functions for general aspects of the tool."""
import re

ERROR_VERSION_MSG = "Tool version is missing or empty."
VALID_VERSION_MSG = "Tool defines a version [%s]."

ERROR_NAME_MSG = "Tool name is missing or empty."
VALID_NAME_MSG = "Tool defines a name [%s]."

ERROR_ID_MSG = "Tool does not define an id attribute."
VALID_ID_MSG = "Tool defines an id [%s]."

lint_tool_types = ["*"]


def lint_general(tool_source, lint_ctx):
    """Check tool version, name, and id."""
    version = tool_source.parse_version()
    if not version:
        lint_ctx.error(ERROR_VERSION_MSG)
    else:
        lint_ctx.valid(VALID_VERSION_MSG % version)

    name = tool_source.parse_name()
    if not name:
        lint_ctx.error(ERROR_NAME_MSG)
    else:
        lint_ctx.valid(VALID_NAME_MSG % name)

    tool_id = tool_source.parse_id()
    if not tool_id:
        lint_ctx.error(ERROR_ID_MSG)
    else:
        lint_ctx.valid(VALID_ID_MSG % tool_id)

    if re.search(r"\s", tool_id):
        lint_ctx.warn("Tool id contains a space - this is discouraged.")
