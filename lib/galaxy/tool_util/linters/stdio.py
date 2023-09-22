"""This module contains a linting functions for tool error detection."""
import re

from galaxy.util import etree
from .command import get_command


def lint_stdio(tool_source, lint_ctx):
    tool_xml = getattr(tool_source, "xml_tree", None)
    if not tool_xml:
        # Can only lint XML tools at this point.
        # Should probably use tool_source.parse_stdio() to abstract away XML details
        return
    stdios = tool_xml.findall("./stdio") if tool_xml else []
    # determine node to report for general problems with stdio
    tool_node = tool_xml.find("./stdio")
    if tool_node is None:
        tool_node = tool_xml.getroot()

    if not stdios:
        command = get_command(tool_xml) if tool_xml else None
        if command is None or not command.get("detect_errors"):
            if tool_source.parse_profile() <= "16.01":
                lint_ctx.info(
                    "No stdio definition found, tool indicates error conditions with output written to stderr.",
                    node=tool_node,
                )
            else:
                lint_ctx.info(
                    "No stdio definition found, tool indicates error conditions with non-zero exit codes.",
                    node=tool_node,
                )
        return

    if len(stdios) > 1:
        lint_ctx.error("More than one stdio tag found, behavior undefined.", node=stdios[1])
        return

    stdio = stdios[0]
    for child in list(stdio):
        if child.tag is etree.Comment:
            continue
        if child.tag == "regex":
            _lint_regex(tool_xml, child, lint_ctx)
        elif child.tag == "exit_code":
            _lint_exit_code(tool_xml, child, lint_ctx)
        else:
            message = "Unknown stdio child tag discovered [%s]. "
            message += "Valid options are exit_code and regex."
            lint_ctx.warn(message % child.tag, node=child)


def _lint_exit_code(tool_xml, child, lint_ctx):
    for key in child.attrib.keys():
        if key not in ["description", "level", "range"]:
            lint_ctx.warn(f"Unknown attribute [{key}] encountered on exit_code tag.", node=child)


def _lint_regex(tool_xml, child, lint_ctx):
    for key in child.attrib.keys():
        if key not in ["description", "level", "match", "source"]:
            lint_ctx.warn(f"Unknown attribute [{key}] encountered on regex tag.", node=child)
    match = child.attrib.get("match")
    if match:
        try:
            re.compile(match)
        except Exception as e:
            lint_ctx.error(f"Match '{match}' is no valid regular expression: {str(e)}", node=child)
