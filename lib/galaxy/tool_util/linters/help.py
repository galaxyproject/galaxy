"""This module contains a linting function for a tool's help."""
from galaxy.util import (
    rst_to_html,
    unicodify,
)


def lint_help(tool_xml, lint_ctx):
    """Ensure tool contains exactly one valid RST help block."""
    # determine node to report for general problems with help
    root = tool_xml.find("./help")
    if root is None:
        root = tool_xml.getroot()
    helps = tool_xml.findall("./help")
    if len(helps) > 1:
        lint_ctx.error("More than one help section found, behavior undefined.", node=helps[1])
        return

    if len(helps) == 0:
        lint_ctx.warn("No help section found, consider adding a help section to your tool.", node=root)
        return

    help_text = helps[0].text or ""
    if not help_text.strip():
        lint_ctx.warn("Help section appears to be empty.", node=helps[0])
        return

    lint_ctx.valid("Tool contains help section.", node=helps[0])

    if "TODO" in help_text:
        lint_ctx.warn("Help contains TODO text.", node=helps[0])

    try:
        rst_to_html(help_text, error=True)
    except Exception as e:
        lint_ctx.warn(f"Invalid reStructuredText found in help - [{unicodify(e)}].", node=helps[0])
        return

    lint_ctx.valid("Help contains valid reStructuredText.", node=helps[0])
