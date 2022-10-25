"""This module contains a linting functions for tool outputs."""
from galaxy.util import (
    etree,
    string_as_bool,
)
from ._util import is_valid_cheetah_placeholder
from ..parser.output_collection_def import NAMED_PATTERNS


def lint_output(tool_xml, lint_ctx):
    """Check output elements, ensure there is at least one and check attributes."""
    outputs = tool_xml.findall("./outputs")
    # determine node to report for general problems with outputs
    tool_node = tool_xml.find("./outputs")
    if tool_node is None:
        tool_node = tool_xml.getroot()
    if len(outputs) == 0:
        lint_ctx.warn("Tool contains no outputs section, most tools should produce outputs.", node=tool_node)
        return
    if len(outputs) > 1:
        lint_ctx.warn("Tool contains multiple output sections, behavior undefined.", node=outputs[1])
    num_outputs = 0
    labels = set()
    names = set()
    for output in list(outputs[0]):
        if output.tag is etree.Comment:
            continue
        if output.tag not in ["data", "collection"]:
            lint_ctx.warn(f"Unknown element found in outputs [{output.tag}]", node=output)
            continue
        num_outputs += 1
        if "name" not in output.attrib:
            lint_ctx.warn("Tool output doesn't define a name - this is likely a problem.", node=output)
            # TODO make this an error if there is no discover_datasets / from_work_dir (is this then still a problem)
        elif not is_valid_cheetah_placeholder(output.attrib["name"]):
            lint_ctx.warn(
                f'Tool output name [{output.attrib["name"]}] is not a valid Cheetah placeholder.', node=output
            )

        name = output.attrib.get("name")
        if name is not None:
            if name in names:
                lint_ctx.error(f"Tool output [{name}] has duplicated name", node=output)
            names.add(name)

        label = output.attrib.get("label", "${tool.name} on ${on_string}")
        if label in labels:
            lint_ctx.error(f"Tool output [{name}] uses duplicated label '{label}'", node=output)
        labels.add(label)

        format_set = False
        if __check_format(output, lint_ctx):
            format_set = True
        if output.tag == "data":
            if "auto_format" in output.attrib and output.attrib["auto_format"]:
                format_set = True

        elif output.tag == "collection":
            if "type" not in output.attrib:
                lint_ctx.warn("Collection output with undefined 'type' found.", node=output)
            if "structured_like" in output.attrib and "inherit_format" in output.attrib:
                format_set = True
        for sub in output:
            if __check_pattern(sub):
                format_set = True
            elif __check_format(sub, lint_ctx, allow_ext=True):
                format_set = True

        if not format_set:
            lint_ctx.warn(
                f"Tool {output.tag} output {output.attrib.get('name', 'with missing name')} doesn't define an output format.",
                node=output,
            )

    # TODO: check for different labels in case of multiple outputs
    lint_ctx.info(f"{num_outputs} outputs found.", node=outputs[0])


def __check_format(node, lint_ctx, allow_ext=False):
    """
    check if format/ext/format_source attribute is set in a given node
    issue a warning if the value is input
    return true (node defines format/ext) / false (else)
    """
    if "format_source" in node.attrib and ("ext" in node.attrib or "format" in node.attrib):
        lint_ctx.warn(
            f"Tool {node.tag} output '{node.attrib.get('name', 'with missing name')}' should use either format_source or format/ext",
            node=node,
        )
    if "format_source" in node.attrib:
        return True
    if node.find(".//action[@type='format']") is not None:
        return True
    # if allowed (e.g. for discover_datasets), ext takes precedence over format
    fmt = None
    if allow_ext:
        fmt = node.attrib.get("ext")
    if fmt is None:
        fmt = node.attrib.get("format")
    if fmt == "input":
        lint_ctx.warn(
            f"Using format='input' on {node.tag}, format_source attribute is less ambiguous and should be used instead.",
            node=node,
        )
    return fmt is not None


def __check_pattern(node):
    """
    check if
    - pattern attribute is set and defines the extension or
    - from_tool_provided_metadata is true
    """
    if node.tag != "discover_datasets":
        return False
    if "from_tool_provided_metadata" in node.attrib and string_as_bool(
        node.attrib.get("from_tool_provided_metadata", "false")
    ):
        return True
    if "pattern" not in node.attrib:
        return False
    pattern = node.attrib["pattern"]
    regex_pattern = NAMED_PATTERNS.get(pattern, pattern)
    # TODO error on wrong pattern or non-regexp
    if "(?P<ext>" in regex_pattern:
        return True
