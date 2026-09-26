"""This module contains linters for a tool's command description.

A command description describes how to build the command-line to execute
from supplied inputs.
"""

from typing import TYPE_CHECKING

from packaging.version import Version

from galaxy.tool_util.lint import Linter

if TYPE_CHECKING:
    from galaxy.tool_util.lint import LintContext
    from galaxy.tool_util.parser.interface import ToolSource

# Profile at which a missing version_command is a warning rather than info;
# older tools are grandfathered, see galaxyproject/planemo#286.
VERSION_COMMAND_WARN_PROFILE = Version("26.2")


class CommandMissing(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext") -> None:
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        root = tool_xml.find("./command")
        if root is None:
            root = tool_xml.getroot()
        command = tool_xml.find("./command")
        if command is None:
            lint_ctx.error(
                "No command tag found, must specify a command template to execute.", linter=cls.name(), node=root
            )


class CommandEmpty(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext") -> None:
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        root = tool_xml.find("./command")
        if root is None:
            root = tool_xml.getroot()
        command = tool_xml.find("./command")
        if command is not None and command.text is None:
            lint_ctx.error("Command is empty.", linter=cls.name(), node=root)


class CommandTODO(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext") -> None:
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        command = tool_xml.find("./command")
        if command is not None and command.text is not None and "TODO" in command.text:
            lint_ctx.warn("Command template contains TODO text.", linter=cls.name(), node=command)


class CommandInterpreterDeprecated(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext") -> None:
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        command = tool_xml.find("./command")
        if command is None:
            return
        interpreter_type = command.attrib.get("interpreter", None)
        if interpreter_type is not None:
            lint_ctx.warn("Command uses deprecated 'interpreter' attribute.", linter=cls.name(), node=command)


class CommandInfo(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext") -> None:
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        command = tool_xml.find("./command")
        if command is None:
            return
        interpreter_info = ""
        if interpreter_type := command.attrib.get("interpreter", None):
            interpreter_info = f" with interpreter of type [{interpreter_type}]"
        lint_ctx.info(f"Tool contains a command{interpreter_info}.", linter=cls.name(), node=command)


def _wraps_external_software(tool_source: "ToolSource") -> bool:
    """Return True if the tool declares a package requirement or a container."""
    requirements, containers, *_ = tool_source.parse_requirements()
    return any(r.type == "package" for r in requirements) or bool(containers)


class VersionCommandMissing(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        if tool_xml.find("./version_command") is not None:
            return
        if not _wraps_external_software(tool_source):
            return
        profile = Version(tool_source.parse_profile())
        report = lint_ctx.warn if profile >= VERSION_COMMAND_WARN_PROFILE else lint_ctx.info
        report(
            "No version_command found, tools wrapping packaged software should report its version.",
            linter=cls.name(),
            node=tool_xml.getroot(),
        )


class VersionCommandMissingNoRequirements(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        if tool_xml.find("./version_command") is not None:
            return
        if _wraps_external_software(tool_source):
            return
        lint_ctx.info(
            "No version_command found, that should be OK for a tool without package requirements.",
            linter=cls.name(),
            node=tool_xml.getroot(),
        )
