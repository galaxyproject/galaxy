"""This module contains a linting function for a tool's help."""

from typing import (
    TYPE_CHECKING,
    Union,
)

from galaxy.tool_util.lint import Linter
from galaxy.util import (
    rst_to_html,
    unicodify,
)

if TYPE_CHECKING:
    from galaxy.tool_util.lint import LintContext
    from galaxy.tool_util.parser.interface import ToolSource


class HelpMissing(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        root = tool_xml.find("./help")
        if root is None:
            root = tool_xml.getroot()
        help = tool_xml.find("./help")
        if help is None:
            lint_ctx.warn(
                "No help section found, consider adding a help section to your tool.", linter=cls.name(), node=root
            )


class HelpEmpty(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        help = tool_xml.find("./help")
        if help is None:
            return
        help_text = help.text or ""
        if not help_text.strip():
            lint_ctx.warn("Help section appears to be empty.", linter=cls.name(), node=help)


class HelpPresent(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        help = tool_xml.find("./help")
        if help is None:
            return
        help_text = help.text or ""
        if help_text.strip():
            lint_ctx.valid("Tool contains help section.", linter=cls.name(), node=help)


class HelpTODO(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        help = tool_xml.find("./help")
        if help is None:
            return
        help_text = help.text or ""
        if "TODO" in help_text:
            lint_ctx.warn("Help contains TODO text.", linter=cls.name(), node=help)


class HelpInvalidRST(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        help = tool_xml.find("./help")
        if help is None:
            return
        help_text = help.text or ""
        if not help_text.strip():
            return
        invalid_rst = rst_invalid(help_text)
        if invalid_rst:
            lint_ctx.warn(f"Invalid reStructuredText found in help - [{invalid_rst}].", linter=cls.name(), node=help)


class HelpValidRST(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        help = tool_xml.find("./help")
        if help is None:
            return
        help_text = help.text or ""
        if not help_text.strip():
            return
        invalid_rst = rst_invalid(help_text)
        if not invalid_rst:
            lint_ctx.valid("Help contains valid reStructuredText.", linter=cls.name(), node=help)


def rst_invalid(text: str) -> Union[bool, str]:
    """
    Predicate to determine if text is invalid reStructuredText.
    Return False if the supplied text is valid reStructuredText or
    a string indicating the problem.
    """
    invalid_rst: Union[bool, str] = False
    try:
        rst_to_html(text, error=True)
    except Exception as e:
        invalid_rst = unicodify(e)
    return invalid_rst
