"""This module contains citation linters.

Citations describe references that should be used when consumers
of the tool publish results.
"""

from typing import TYPE_CHECKING

from pydantic import ValidationError

from galaxy.tool_util.lint import Linter
from galaxy.tool_util.version import parse_version
from galaxy.tool_util_models.tool_source import Citation

# Profile at which invalid citations stop loading fatally rather than being
# dropped; see galaxyproject/galaxy#22795.
CITATION_FATAL_PROFILE = parse_version("26.1")

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


class CitationsInvalid(Linter):
    """Surface citations that the ``Citation`` model would reject at tool load.

    Reuses the same pydantic validation the parser uses so the linter reports
    exactly what fails to load, plus the legacy ``doi:`` prefix that is accepted
    but normalized. For tools targeting profile >= 26.1 these are errors (an
    invalid citation prevents loading and the legacy prefix is no longer
    tolerated); for older profiles they are warnings (the citation is dropped).
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        citations = tool_xml.find("citations")
        if citations is None:
            return
        report = (
            lint_ctx.error if parse_version(tool_source.parse_profile()) >= CITATION_FATAL_PROFILE else lint_ctx.warn
        )
        for citation in citations:
            content = (citation.text or "").strip()
            if not content:
                # Empty citations are reported by CitationsNoText.
                continue
            # An absent type routes to the model's content-shape check (a useful
            # message) rather than failing on the required str field.
            citation_type = citation.attrib.get("type") or ""
            try:
                parsed = Citation(type=citation_type, content=content)
            except ValidationError as e:
                report(
                    f"Citation '{content}' is invalid and will not load for tools with profile >= 26.1 "
                    f"(and is dropped for older profiles): {e.errors()[0]['msg']}",
                    linter=cls.name(),
                    node=citation,
                )
                continue
            if parsed.content != content:
                report(
                    f"Citation '{content}' uses the legacy 'doi:' prefix; use the bare DOI '{parsed.content}' instead.",
                    linter=cls.name(),
                    node=citation,
                )


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
