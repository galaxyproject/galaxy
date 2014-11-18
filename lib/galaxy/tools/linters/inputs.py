

def lint_inputs(tool_xml, lint_ctx):
    inputs = tool_xml.findall("./inputs//param")
    num_inputs = 0
    for param in inputs:
        num_inputs += 1
        param_attrib = param.attrib
        has_errors = False
        if "type" not in param_attrib:
            lint_ctx.error("Found param input with type specified.")
            has_errors = True
        if "name" not in param_attrib:
            lint_ctx.error("Found param input with not name specified.")
            has_errors = True

        if has_errors:
            continue

        param_type = param_attrib["type"]
        param_name = param_attrib["name"]
        if param_type == "data_input":
            if "format" not in param_attrib:
                lint_ctx.warn("Found param input %s contains no format specified - 'data' format will be assumed.", param_name)
        # TODO: Validate type, much more...
    if num_inputs:
        lint_ctx.info("Found %d input parameters.", num_inputs)
    else:
        lint_ctx.warn("Found not input parameters.")


def lint_repeats(tool_xml, lint_ctx):
    repeats = tool_xml.findall("./inputs//repeat")
    for repeat in repeats:
        if "name" not in repeat.attrib:
            lint_ctx.error("Repeat does not specify name attribute.")
        if "title" not in repeat.attrib:
            lint_ctx.error("Repeat does not specify title attribute.")
