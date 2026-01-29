"""This module contains citation linters.

Citations describe references that should be used when consumers
of the tool publish results.
"""

from typing import TYPE_CHECKING

from galaxy.tool_util.lint import Linter

if TYPE_CHECKING:
    from galaxy.tool_util.lint import LintContext
    from galaxy.tool_util.parser.interface import ToolSource


class CitationsMissing(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        root = tool_xml.find("./citations")
        if root is None:
            root = tool_xml.getroot()
        citations = tool_xml.findall("citations")
        if len(citations) == 0:
            lint_ctx.warn("No citations found, consider adding citations to your tool.", linter=cls.name(), node=root)


class CitationsNoText(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        citations = tool_xml.find("citations")
        if citations is None:
            return
        for citation in citations:
            citation_type = citation.attrib.get("type")
            if citation_type in ["doi", "bibtex"] and (citation.text is None or not citation.text.strip()):
                lint_ctx.error(f"Empty {citation_type} citation.", linter=cls.name(), node=citation)


class CitationsFound(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        root = tool_xml.find("./citations")
        if root is None:
            root = tool_xml.getroot()
        citations = tool_xml.find("citations")

        if citations is not None and len(citations) > 0:
            lint_ctx.valid(f"Found {len(citations)} citations.", linter=cls.name(), node=root)


class CitationsNoValid(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        root = tool_xml.find("./citations")
        if root is None:
            root = tool_xml.getroot()
        citations = tool_xml.findall("citations")
        if len(citations) != 1:
            return
        if len(citations[0]) == 0:
            lint_ctx.warn("Found no valid citations.", linter=cls.name(), node=root)
