"""This module contains linting functions for general aspects of the tool."""
import re

import packaging.version

ERROR_VERSION_MSG = "Tool version is missing or empty."
WARN_VERSION_MSG = "Tool version [%s] is not compliant with PEP 440."
VALID_VERSION_MSG = "Tool defines a version [%s]."

ERROR_NAME_MSG = "Tool name is missing or empty."
VALID_NAME_MSG = "Tool defines a name [%s]."

ERROR_ID_MSG = "Tool does not define an id attribute."
VALID_ID_MSG = "Tool defines an id [%s]."

PROFILE_PATTERN = re.compile(r"^[1,2]\d\.[0,1]\d$")
PROFILE_INFO_DEFAULT_MSG = "Tool targets 16.01 Galaxy profile."
PROFILE_INFO_SPECIFIED_MSG = "Tool specifies profile version [%s]."
PROFILE_INVALID_MSG = "Tool specifies an invalid profile version [%s]."

WARN_WHITESPACE_MSG = "%s contains whitespace, this may cause errors: [%s]."
WARN_ID_WHITESPACE_MSG = (
    "Tool ID contains whitespace - this is discouraged: [%s].")

lint_tool_types = ["*"]


def lint_general(tool_source, lint_ctx):
    """Check tool version, name, and id."""
    version = tool_source.parse_version() or ''
    parsed_version = packaging.version.parse(version)
    if not version:
        lint_ctx.error(ERROR_VERSION_MSG)
    elif isinstance(parsed_version, packaging.version.LegacyVersion):
        lint_ctx.warn(WARN_VERSION_MSG % version)
    elif version != version.strip():
        lint_ctx.warn(WARN_WHITESPACE_MSG % ('Tool version', version))
    else:
        lint_ctx.valid(VALID_VERSION_MSG % version)

    name = tool_source.parse_name()
    if not name:
        lint_ctx.error(ERROR_NAME_MSG)
    elif name != name.strip():
        lint_ctx.warn(WARN_WHITESPACE_MSG % ('Tool name', name))
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
        lint_ctx.error(PROFILE_INVALID_MSG)
    elif profile == "16.01":
        lint_ctx.valid(PROFILE_INFO_DEFAULT_MSG)
    else:
        lint_ctx.valid(PROFILE_INFO_SPECIFIED_MSG % profile)

    requirements, containers = tool_source.parse_requirements_and_containers()
    for r in requirements:
        if r.type == "package":
            if not r.name:
                lint_ctx.error("Requirement without name found")
            if not r.version:
                lint_ctx.warn(f"Requirement {r.name} defines no version")
            # Warn requirement attributes with leading/trailing whitespace:
            elif r.version != r.version.strip():
                lint_ctx.warn(
                    WARN_WHITESPACE_MSG % ('Requirement version', r.version))

    if re.search(r"\s", tool_id):
        lint_ctx.warn(WARN_ID_WHITESPACE_MSG % tool_id)
