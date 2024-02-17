"""This module contains a linting functions for tool error detection."""

import re
from typing import TYPE_CHECKING

from packaging.version import Version

from galaxy.tool_util.lint import Linter

if TYPE_CHECKING:
    from galaxy.tool_util.lint import LintContext
    from galaxy.tool_util.parser.interface import ToolSource


class StdIOAbsenceLegacy(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            # Can only lint XML tools at this point.
            # Should probably use tool_source.parse_stdio() to abstract away XML details
            return
        stdios = tool_xml.findall("./stdio") if tool_xml else []
        if stdios:
            return
        tool_node = tool_xml.getroot()
        command = tool_xml.find("./command")
        if command is None or not command.get("detect_errors"):
            if Version(tool_source.parse_profile()) <= Version("16.01"):
                lint_ctx.info(
                    "No stdio definition found, tool indicates error conditions with output written to stderr.",
                    linter=cls.name(),
                    node=tool_node,
                )


class StdIOAbsence(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            # Can only lint XML tools at this point.
            # Should probably use tool_source.parse_stdio() to abstract away XML details
            return
        stdios = tool_xml.findall("./stdio") if tool_xml else []
        if stdios:
            return
        tool_node = tool_xml.getroot()
        command = tool_xml.find("./command")
        if command is None or not command.get("detect_errors"):
            if Version(tool_source.parse_profile()) > Version("16.01"):
                lint_ctx.info(
                    "No stdio definition found, tool indicates error conditions with non-zero exit codes.",
                    linter=cls.name(),
                    node=tool_node,
                )


class StdIORegex(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            # Can only lint XML tools at this point.
            # Should probably use tool_source.parse_stdio() to abstract away XML details
            return
        stdios = tool_xml.findall("./stdio") if tool_xml else []

        if len(stdios) != 1:
            return

        stdio = stdios[0]
        for child in list(stdio):
            if child.tag == "regex":
                match = child.attrib.get("match")
                if match:
                    try:
                        re.compile(match)
                    except Exception as e:
                        lint_ctx.error(
                            f"Match '{match}' is no valid regular expression: {str(e)}", linter=cls.name(), node=child
                        )
