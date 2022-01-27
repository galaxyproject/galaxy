"""This module contains a linting function for a tool's command description.

A command description describes how to build the command-line to execute
from supplied inputs.
"""


def lint_command(tool_xml, lint_ctx):
    """Ensure tool contains exactly one command and check attributes."""
    root = tool_xml.find("./command")
    if root is None:
        root = tool_xml.getroot()

    commands = tool_xml.findall("./command")
    if len(commands) > 1:
        lint_ctx.error("More than one command tag found, behavior undefined.", node=commands[1])
        return

    if len(commands) == 0:
        lint_ctx.error("No command tag found, must specify a command template to execute.", node=root)
        return

    command = get_command(tool_xml)
    if command.text is None:
        lint_ctx.error("Command is empty.", node=root)
    elif "TODO" in command.text:
        lint_ctx.warn("Command template contains TODO text.", node=command)

    command_attrib = command.attrib
    interpreter_type = None
    for key, value in command_attrib.items():
        if key == "interpreter":
            interpreter_type = value
        elif key == "detect_errors":
            detect_errors = value
            if detect_errors not in ["default", "exit_code", "aggressive"]:
                lint_ctx.warn(f"Unknown detect_errors attribute [{detect_errors}]", node=command)

    interpreter_info = ""
    if interpreter_type:
        interpreter_info = f" with interpreter of type [{interpreter_type}]"
    if interpreter_type:
        lint_ctx.warn("Command uses deprecated 'interpreter' attribute.", node=command)
    lint_ctx.info(f"Tool contains a command{interpreter_info}.", node=command)


def get_command(tool_xml):
    """Get command XML element from supplied XML root."""
    root = tool_xml.getroot()
    commands = root.findall("command")
    command = None
    if len(commands) == 1:
        command = commands[0]
    return command
