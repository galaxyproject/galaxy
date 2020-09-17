"""This module contains a linting functions for tool outputs."""
from ._util import is_valid_cheetah_placeholder


def lint_output(tool_xml, lint_ctx):
    """Check output elements, ensure there is at least one and check attributes."""
    outputs = tool_xml.findall("./outputs")
    if len(outputs) == 0:
        lint_ctx.warn("Tool contains no outputs section, most tools should produce outputs.")
    if len(outputs) > 1:
        lint_ctx.warn("Tool contains multiple output sections, behavior undefined.")

    num_outputs = 0
    if len(outputs) == 0:
        lint_ctx.warn("No outputs found")
        return

    for output in list(outputs[0]):
        if output.tag not in ["data", "collection"]:
            lint_ctx.warn("Unknown element found in outputs [%s]" % output.tag)
            continue
        num_outputs += 1
        if "name" not in output.attrib:
            lint_ctx.warn("Tool output doesn't define a name - this is likely a problem.")
        else:
            if not is_valid_cheetah_placeholder(output.attrib["name"]):
                lint_ctx.warn("Tool output name [%s] is not a valid Cheetah placeholder.", output.attrib["name"])

        format_set = False
        if output.tag == "data":
            if __check_format(output, lint_ctx):
                format_set = True
            elif "auto_format" in output.attrib and output.attrib["auto_format"]:
                format_set = True

        elif output.tag == "collection":
            if "type" not in output.attrib:
                lint_ctx.warn("Collection output with undefined 'type' found.")
            if "structured_like" in output.attrib and "inherit_format" in output.attrib:
                format_set = True
        if "format_source" in output.attrib:
            format_set = True
        for sub in output:
            if __check_pattern(sub):
                format_set = True
            elif __check_format(sub, lint_ctx):
                format_set = True

        if not format_set:
            lint_ctx.warn("Tool {} output {} doesn't define an output format.".format(output.tag, output.attrib.get("name", "with missing name")))

    lint_ctx.info("%d outputs found.", num_outputs)


def __check_format(node, lint_ctx):
    """
    check if format/ext attribute is set in a given node
    issue a warning if the value is input
    return true (node defines format/ext) / false (else)
    """
    fmt = node.attrib.get("format", node.attrib.get("ext", None))
    if fmt == "input":
        lint_ctx.warn("Using format='input' on %s, format_source attribute is less ambiguous and should be used instead." % node.tag)
    return fmt is not None


def __check_pattern(node):
    """
    check if pattern attribute is set and defines the extension
    """
    if node.tag != "discover_datasets":
        return False
    if "pattern" not in node.attrib:
        return False
    if node.attrib["pattern"] == "__default__":
        return True
    if "ext" in node.attrib["pattern"] and node.attrib["pattern"].startswith("__") and node.attrib["pattern"].endswith("__"):
        return True
