

def lint_command(tool_xml, lint_ctx):
    root = tool_xml.getroot()
    commands = root.findall("command")
    if len(commands) > 1:
        lint_ctx.error("More than one command tag found, behavior undefined.")
        return

    if len(commands) == 0:
        lint_ctx.error("No command tag found, must specify a command template to execute.")
        return

    command = commands[0]
    if "TODO" in command:
        lint_ctx.warn("Command template contains TODO text.")

    lint_ctx.info("Tool contains a command.")
