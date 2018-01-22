"""This module contains a linting functions for general aspects of the tool."""
import re

ERROR_VERSION_MSG = "Tool version is missing or empty."
VALID_VERSION_MSG = "Tool defines a version [%s]."

ERROR_NAME_MSG = "Tool name is missing or empty."
VALID_NAME_MSG = "Tool defines a name [%s]."

ERROR_ID_MSG = "Tool does not define an id attribute."
VALID_ID_MSG = "Tool defines an id [%s]."

PROFILE_PATTERN = re.compile(r"^[1,2]\d\.[0,1]\d$")
PROFILE_INFO_DEFAULT_MSG = "Tool targets 16.01 Galaxy profile."
PROFILE_INFO_SPECIFIED_MSG = "Tool specifies profile version [%s]."
PROFILE_INVALID_MSG = "Tool specifies an invalid profile version [%s]."

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

    profile = tool_source.parse_profile()
    profile_valid = PROFILE_PATTERN.match(profile) is not None
    if not profile_valid:
        lint_ctx.warn(PROFILE_INVALID_MSG)
    elif profile == "16.01":
        lint_ctx.valid(PROFILE_INFO_DEFAULT_MSG)
    else:
        lint_ctx.valid(PROFILE_INFO_SPECIFIED_MSG % profile)

    if re.search(r"\s", tool_id):
        lint_ctx.warn("Tool id contains a space - this is discouraged.")
