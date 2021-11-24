"""This module contains a linting functions for tool error detection."""
from .command import get_command


def lint_stdio(tool_source, lint_ctx):
    tool_xml = getattr(tool_source, "xml_tree", None)
    # determine line to report for general problems with stdio
    try:
        tool_line = tool_xml.find("./tool").sourceline
        tool_path = tool_xml.getpath(tool_xml.find("./tool"))
    except AttributeError:
        tool_line = 0
        tool_path = None
    stdios = tool_xml.findall("./stdio") if tool_xml else []

    if not stdios:
        command = get_command(tool_xml) if tool_xml else None
        if command is None or not command.get("detect_errors"):
            if tool_source.parse_profile() <= "16.01":
                lint_ctx.info("No stdio definition found, tool indicates error conditions with output written to stderr.", line=tool_line, xpath=tool_path)
            else:
                lint_ctx.info("No stdio definition found, tool indicates error conditions with non-zero exit codes.", line=tool_line, xpath=tool_path)
        return

    if len(stdios) > 1:
        lint_ctx.error("More than one stdio tag found, behavior undefined.", line=stdios[1].sourceline, xpath=tool_xml.getpath(stdios[1]))
        return

    stdio = stdios[0]
    for child in list(stdio):
        if child.tag == "regex":
            _lint_regex(tool_xml, child, lint_ctx)
        elif child.tag == "exit_code":
            _lint_exit_code(tool_xml, child, lint_ctx)
        else:
            message = "Unknown stdio child tag discovered [%s]. "
            message += "Valid options are exit_code and regex."
            lint_ctx.warn(message % child.tag, line=child.sourceline, xpath=tool_xml.getpath(child))


def _lint_exit_code(tool_xml, child, lint_ctx):
    for key in child.attrib.keys():
        if key not in ["description", "level", "range"]:
            lint_ctx.warn(f"Unknown attribute [{key}] encountered on exit_code tag.", line=child.sourceline, xpath=tool_xml.getpath(child))


def _lint_regex(tool_xml, child, lint_ctx):
    for key in child.attrib.keys():
        if key not in ["description", "level", "match", "source"]:
            lint_ctx.warn(f"Unknown attribute [{key}] encountered on regex tag.", line=child.sourceline, xpath=tool_xml.getpath(child))
