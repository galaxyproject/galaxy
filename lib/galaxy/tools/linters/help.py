from galaxy.util import rst_to_html


def lint_help(tool_xml, lint_ctx):
    root = tool_xml.getroot()
    helps = root.findall("help")
    if len(helps) > 1:
        lint_ctx.error("More than one help section found, behavior undefined.")
        return

    if len(helps) == 0:
        lint_ctx.warn("No help section found, consider adding a help section to your tool.")
        return

    help = helps[0].text or ''
    if not help.strip():
        lint_ctx.warn("Help section appears to be empty.")
        return

    lint_ctx.valid("Tool contains help section.")
    invalid_rst = rst_invalid(help)

    if "TODO" in help:
        lint_ctx.warn("Help contains TODO text.")

    if invalid_rst:
        lint_ctx.warn("Invalid reStructuredText found in help - [%s]." % invalid_rst)
    else:
        lint_ctx.valid("Help contains valid reStructuredText.")


def rst_invalid(text):
    invalid_rst = False
    try:
        rst_to_html(text)
    except Exception as e:
        invalid_rst = str(e)
    return invalid_rst
