

def lint_output(tool_xml, lint_ctx):
    outputs = tool_xml.findall("./outputs/data")
    if not outputs:
        lint_ctx.warn("Tool contains no outputs, most tools should produce outputs..")
        return

    num_outputs = 0
    for output in outputs:
        num_outputs += 1
        output_attrib = output.attrib
        format_set = False
        if "format" in output_attrib:
            format_set = True
            format = output_attrib["format"]
            if format == "input":
                lint_ctx.warn("Using format='input' on output data, format_source attribute is less ambigious and should be used instead.")
        elif "format_source" in output_attrib:
            format_set = True

        if not format_set:
            lint_ctx.warn("Tool data output doesn't define an output format.")

    lint_ctx.info("%d output datasets found.", num_outputs)
