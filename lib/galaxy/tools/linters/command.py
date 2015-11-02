

def lint_command(tool_xml, lint_ctx):
    root = tool_xml.getroot()
    commands = root.findall("command")
    if len(commands) > 1:
        lint_ctx.error("More than one command tag found, behavior undefined.")
        return

    if len(commands) == 0:
        lint_ctx.error("No command tag found, must specify a command template to execute.")
        return

    command = get_command(tool_xml)
    if "TODO" in command:
        lint_ctx.warn("Command template contains TODO text.")

    command_attrib = command.attrib
    interpreter_type = None
    for key, value in command_attrib.items():
        if key == "interpreter":
            interpreter_type = value
        elif key == "detect_errors":
            detect_errors = value
            if detect_errors not in ["default", "exit_code", "aggressive"]:
                lint_ctx.warn("Unknown detect_errors attribute [%s]" % detect_errors)
        else:
            lint_ctx.warn("Unknown attribute [%s] encountered on command tag." % key)

    interpreter_info = ""
    if interpreter_type:
        interpreter_info = " with interpreter of type [%s]" % interpreter_type
    lint_ctx.info("Tool contains a command%s." % interpreter_info)


def get_command(tool_xml):
    root = tool_xml.getroot()
    commands = root.findall("command")
    command = None
    if len(commands) == 1:
        command = commands[0]
    return command
