

def lint_help(tool_xml, lint_ctx):
    root = tool_xml.getroot()
    helps = root.findall("help")
    if len(helps) > 1:
        lint_ctx.error("More than one help section found, behavior undefined.")
        return

    if len(helps) == 0:
        lint_ctx.warn("No help section found, consider adding a help section to your tool.")
        return

    # TODO: validate help section RST.
    lint_ctx.valid("Tool contains help section.")
