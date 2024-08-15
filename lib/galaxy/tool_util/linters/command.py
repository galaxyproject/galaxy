"""This module contains linters for a tool's command description.

A command description describes how to build the command-line to execute
from supplied inputs.
"""

from typing import TYPE_CHECKING

from galaxy.tool_util.lint import Linter

if TYPE_CHECKING:
    from galaxy.tool_util.lint import LintContext
    from galaxy.tool_util.parser.interface import ToolSource


class CommandMissing(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
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
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
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
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        command = tool_xml.find("./command")
        if command is not None and command.text is not None and "TODO" in command.text:
            lint_ctx.warn("Command template contains TODO text.", linter=cls.name(), node=command)


class CommandInterpreterDeprecated(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
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
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        command = tool_xml.find("./command")
        if command is None:
            return
        interpreter_type = command.attrib.get("interpreter", None)
        interpreter_info = ""
        if interpreter_type:
            interpreter_info = f" with interpreter of type [{interpreter_type}]"
        lint_ctx.info(f"Tool contains a command{interpreter_info}.", linter=cls.name(), node=command)
