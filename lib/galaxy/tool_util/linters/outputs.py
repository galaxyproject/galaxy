"""This module contains a linting functions for tool outputs."""
from galaxy.util import string_as_bool
from ._util import is_valid_cheetah_placeholder
from ..parser.output_collection_def import NAMED_PATTERNS


def lint_output(tool_xml, lint_ctx):
    """Check output elements, ensure there is at least one and check attributes."""
    # determine line to report for general problems with outputs
    try:
        tool_line = tool_xml.find("./tool").sourceline
        tool_path = tool_xml.getpath(tool_xml.find("./tool"))
    except AttributeError:
        tool_line = 0
        tool_path = None
    outputs = tool_xml.findall("./outputs")
    if len(outputs) == 0:
        lint_ctx.warn("Tool contains no outputs section, most tools should produce outputs.", line=tool_line, xpath=tool_path)
        return
    if len(outputs) > 1:
        lint_ctx.warn("Tool contains multiple output sections, behavior undefined.", line=outputs[1].sourceline, xpath=tool_xml.getpath(outputs[1]))
    num_outputs = 0
    for output in list(outputs[0]):
        if output.tag not in ["data", "collection"]:
            lint_ctx.warn(f"Unknown element found in outputs [{output.tag}]", line=output.sourceline, xpath=tool_xml.getpath(output))
            continue
        num_outputs += 1
        if "name" not in output.attrib:
            lint_ctx.warn("Tool output doesn't define a name - this is likely a problem.", line=output.sourceline, xpath=tool_xml.getpath(output))
        else:
            if not is_valid_cheetah_placeholder(output.attrib["name"]):
                lint_ctx.warn("Tool output name [%s] is not a valid Cheetah placeholder.", output.attrib["name"], line=output.sourceline, xpath=tool_xml.getpath(output))

        format_set = False
        if __check_format(tool_xml, output, lint_ctx):
            format_set = True
        if output.tag == "data":
            if "auto_format" in output.attrib and output.attrib["auto_format"]:
                format_set = True

        elif output.tag == "collection":
            if "type" not in output.attrib:
                lint_ctx.warn("Collection output with undefined 'type' found.", line=output.sourceline, xpath=tool_xml.getpath(output))
            if "structured_like" in output.attrib and "inherit_format" in output.attrib:
                format_set = True
        for sub in output:
            if __check_pattern(sub):
                format_set = True
            elif __check_format(tool_xml, sub, lint_ctx, allow_ext=True):
                format_set = True

        if not format_set:
            lint_ctx.warn(f"Tool {output.tag} output {output.attrib.get('name', 'with missing name')} doesn't define an output format.", line=output.sourceline, xpath=tool_xml.getpath(output))

    lint_ctx.info(f"{num_outputs} outputs found.", line=outputs[0].sourceline)


def __check_format(tool_xml, node, lint_ctx, allow_ext=False):
    """
    check if format/ext/format_source attribute is set in a given node
    issue a warning if the value is input
    return true (node defines format/ext) / false (else)
    """
    if "format_source" in node.attrib and ("ext" in node.attrib or "format" in node.attrib):
        lint_ctx.warn(f"Tool {node.tag} output {node.attrib.get('name', 'with missing name')} should use either format_source or format/ext", line=node.sourceline, xpath=tool_xml.getpath(node))
    if "format_source" in node.attrib:
        return True
    # if allowed (e.g. for discover_datasets), ext takes precedence over format
    fmt = None
    if allow_ext:
        fmt = node.attrib.get("ext")
    if fmt is None:
        fmt = node.attrib.get("format")
    if fmt == "input":
        lint_ctx.warn(f"Using format='input' on {node.tag}, format_source attribute is less ambiguous and should be used instead.", line=node.sourceline, xpath=tool_xml.getpath(node))
    return fmt is not None


def __check_pattern(node):
    """
    check if
    - pattern attribute is set and defines the extension or
    - from_tool_provided_metadata is true
    """
    if node.tag != "discover_datasets":
        return False
    if "from_tool_provided_metadata" in node.attrib and string_as_bool(node.attrib.get("from_tool_provided_metadata", "false")):
        return True
    if "pattern" not in node.attrib:
        return False
    pattern = node.attrib["pattern"]
    regex_pattern = NAMED_PATTERNS.get(pattern, pattern)
    if "(?P<ext>" in regex_pattern:
        return True
