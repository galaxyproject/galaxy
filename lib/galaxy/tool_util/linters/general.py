"""This module contains linting functions for general aspects of the tool."""
import re
from typing import (
    Tuple,
    TYPE_CHECKING,
)

from galaxy.tool_util.lint import Linter
from galaxy.tool_util.version import (
    LegacyVersion,
    parse_version,
)

if TYPE_CHECKING:
    from galaxy.tool_util.lint import LintContext
    from galaxy.tool_util.parser.interface import ToolSource
    from galaxy.util.etree import (
        Element,
        ElementTree,
    )

PROFILE_PATTERN = re.compile(r"^[12]\d\.\d{1,2}$")


lint_tool_types = ["*"]


def _tool_xml_and_root(tool_source: "ToolSource") -> Tuple["ElementTree", "Element"]:
    tool_xml = getattr(tool_source, "xml_tree", None)
    if tool_xml:
        tool_node = tool_xml.getroot()
    else:
        tool_node = None
    return tool_xml, tool_node


class ToolVersionMissing(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml, tool_node = _tool_xml_and_root(tool_source)
        version = tool_source.parse_version() or ""
        if not version:
            lint_ctx.error("Tool version is missing or empty.", node=tool_node)


class ToolVersionPEP404(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml, tool_node = _tool_xml_and_root(tool_source)
        version = tool_source.parse_version() or ""
        parsed_version = parse_version(version)
        if version and isinstance(parsed_version, LegacyVersion):
            lint_ctx.warn(f"Tool version [{version}] is not compliant with PEP 440.", node=tool_node)


class ToolVersionWhitespace(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml, tool_node = _tool_xml_and_root(tool_source)
        version = tool_source.parse_version() or ""
        if version != version.strip():
            lint_ctx.warn(
                f"Tool version is pre/suffixed by whitespace, this may cause errors: [{version}].", node=tool_node
            )


class ToolVersionValid(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml, tool_node = _tool_xml_and_root(tool_source)
        version = tool_source.parse_version() or ""
        parsed_version = parse_version(version)
        if version and not isinstance(parsed_version, LegacyVersion) and version == version.strip():
            lint_ctx.valid(f"Tool defines a version [{version}].", node=tool_node)


class ToolNameMissing(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        _, tool_node = _tool_xml_and_root(tool_source)
        name = tool_source.parse_name()
        if not name:
            lint_ctx.error("Tool name is missing or empty.", node=tool_node)


class ToolNameWhitespace(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        _, tool_node = _tool_xml_and_root(tool_source)
        name = tool_source.parse_name()
        if name and name != name.strip():
            lint_ctx.warn(f"Tool name is pre/suffixed by whitespace, this may cause errors: [{name}].", node=tool_node)


class ToolNameValid(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        _, tool_node = _tool_xml_and_root(tool_source)
        name = tool_source.parse_name()
        if name and name == name.strip():
            lint_ctx.valid(f"Tool defines a name [{name}].", node=tool_node)


class ToolIDMissing(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        _, tool_node = _tool_xml_and_root(tool_source)
        tool_id = tool_source.parse_id()
        if not tool_id:
            lint_ctx.error("Tool does not define an id attribute.", node=tool_node)


class ToolIDWhitespace(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        _, tool_node = _tool_xml_and_root(tool_source)
        tool_id = tool_source.parse_id()
        if tool_id and re.search(r"\s", tool_id):
            lint_ctx.warn(f"Tool ID contains whitespace - this is discouraged: [{tool_id}].", node=tool_node)


class ToolIDValid(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        _, tool_node = _tool_xml_and_root(tool_source)
        tool_id = tool_source.parse_id()
        if tool_id and not re.search(r"\s", tool_id):
            lint_ctx.valid(f"Tool defines an id [{tool_id}].", node=tool_node)


class ToolProfileInvalid(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        _, tool_node = _tool_xml_and_root(tool_source)
        profile = tool_source.parse_profile()
        profile_valid = PROFILE_PATTERN.match(profile) is not None
        if not profile_valid:
            lint_ctx.error(f"Tool specifies an invalid profile version [{profile}].", node=tool_node)


class ToolProfileLegacy(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        _, tool_node = _tool_xml_and_root(tool_source)
        profile = tool_source.parse_profile()
        profile_valid = PROFILE_PATTERN.match(profile) is not None
        if profile_valid and profile == "16.01":
            lint_ctx.valid("Tool targets 16.01 Galaxy profile.", node=tool_node)


class ToolProfileValid(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        _, tool_node = _tool_xml_and_root(tool_source)
        profile = tool_source.parse_profile()
        profile_valid = PROFILE_PATTERN.match(profile) is not None
        if profile_valid and profile != "16.01":
            lint_ctx.valid(f"Tool specifies profile version [{profile}].", node=tool_node)


class RequirementNameMissing(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        _, tool_node = _tool_xml_and_root(tool_source)
        requirements, containers, resource_requirements = tool_source.parse_requirements_and_containers()
        for r in requirements:
            if r.type != "package":
                continue
            if not r.name:
                lint_ctx.error("Requirement without name found")


class RequirementVersionMissing(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        _, tool_node = _tool_xml_and_root(tool_source)
        requirements, containers, resource_requirements = tool_source.parse_requirements_and_containers()
        for r in requirements:
            if r.type != "package":
                continue
            if not r.version:
                lint_ctx.warn(f"Requirement {r.name} defines no version")


class RequirementVersionWhitespace(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        _, tool_node = _tool_xml_and_root(tool_source)
        requirements, containers, resource_requirements = tool_source.parse_requirements_and_containers()
        for r in requirements:
            if r.type != "package":
                continue
            if r.version and r.version != r.version.strip():
                lint_ctx.warn(f"Requirement version contains whitespace, this may cause errors: [{r.version}].")


class RessourceRequirementExpression(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        _, tool_node = _tool_xml_and_root(tool_source)
        requirements, containers, resource_requirements = tool_source.parse_requirements_and_containers()
        for rr in resource_requirements:
            if rr.runtime_required:
                lint_ctx.warn("Expressions in resource requirement not supported yet")
