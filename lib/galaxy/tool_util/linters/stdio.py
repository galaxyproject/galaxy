"""This module contains a linting functions for tool error detection."""
import re

from ._util import node_props_factory
from .command import get_command


def lint_stdio(tool_source, lint_ctx):
    tool_xml = getattr(tool_source, "xml_tree", None)
    if not tool_xml:
        # Can only lint XML tools at this point.
        # Should probably use tool_source.parse_stdio() to abstract away XML details
        return
    # determine node to report for general problems with stdio
    node_props = node_props_factory(tool_xml)
    tool_node = tool_xml.find("./tool")
    stdios = tool_xml.findall("./stdio") if tool_xml else []

    if not stdios:
        command = get_command(tool_xml) if tool_xml else None
        if command is None or not command.get("detect_errors"):
            if tool_source.parse_profile() <= "16.01":
                lint_ctx.info("No stdio definition found, tool indicates error conditions with output written to stderr.", **node_props(tool_node))
            else:
                lint_ctx.info("No stdio definition found, tool indicates error conditions with non-zero exit codes.", **node_props(tool_node))
        return

    if len(stdios) > 1:
        lint_ctx.error("More than one stdio tag found, behavior undefined.", **node_props(stdios[1]))
        return

    stdio = stdios[0]
    for child in list(stdio):
        if child.tag == "regex":
            _lint_regex(tool_xml, child, lint_ctx, node_props)
        elif child.tag == "exit_code":
            _lint_exit_code(tool_xml, child, lint_ctx, node_props)
        else:
            message = "Unknown stdio child tag discovered [%s]. "
            message += "Valid options are exit_code and regex."
            lint_ctx.warn(message % child.tag, **node_props(child))


def _lint_exit_code(tool_xml, child, lint_ctx, node_props):
    for key in child.attrib.keys():
        if key not in ["description", "level", "range"]:
            lint_ctx.warn(f"Unknown attribute [{key}] encountered on exit_code tag.", **node_props(child))


def _lint_regex(tool_xml, child, lint_ctx, node_props):
    for key in child.attrib.keys():
        if key not in ["description", "level", "match", "source"]:
            lint_ctx.warn(f"Unknown attribute [{key}] encountered on regex tag.", **node_props(child))
    match = child.attrib.get("match")
    if match:
        try:
            re.compile(match)
        except Exception as e:
            lint_ctx.error(f"Match '{match}' is no valid regular expression: {str(e)}", **node_props(child))
