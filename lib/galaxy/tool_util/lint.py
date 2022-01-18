"""This modules contains the functions that drive the tool linting framework."""

import inspect

from galaxy.tool_util.parser import get_tool_source
from galaxy.util import submodules


LEVEL_ALL = "all"
LEVEL_WARN = "warn"
LEVEL_ERROR = "error"


def lint_tool_source(tool_source, level=LEVEL_ALL, fail_level=LEVEL_WARN, extra_modules=None, skip_types=None, name=None):
    extra_modules = extra_modules or []
    skip_types = skip_types or []
    lint_context = LintContext(level=level, skip_types=skip_types, object_name=name)
    lint_tool_source_with(lint_context, tool_source, extra_modules)

    return not lint_context.failed(fail_level)


def lint_xml(tool_xml, level=LEVEL_ALL, fail_level=LEVEL_WARN, extra_modules=None, skip_types=None, name=None):
    extra_modules = extra_modules or []
    skip_types = skip_types or []
    lint_context = LintContext(level=level, skip_types=skip_types, object_name=name)
    lint_xml_with(lint_context, tool_xml, extra_modules)

    return not lint_context.failed(fail_level)


def lint_tool_source_with(lint_context, tool_source, extra_modules=None):
    extra_modules = extra_modules or []
    import galaxy.tool_util.linters
    tool_xml = getattr(tool_source, "xml_tree", None)
    linter_modules = submodules.import_submodules(galaxy.tool_util.linters, ordered=True)
    linter_modules.extend(extra_modules)
    for module in linter_modules:
        tool_type = tool_source.parse_tool_type() or "default"
        lint_tool_types = getattr(module, "lint_tool_types", ["default"])
        if not ("*" in lint_tool_types or tool_type in lint_tool_types):
            continue

        for (name, value) in inspect.getmembers(module):
            if callable(value) and name.startswith("lint_"):
                # Look at the first argument to the linter to decide
                # if we should lint the XML description or the abstract
                # tool parser object.
                first_arg = inspect.getfullargspec(value).args[0]
                if first_arg == "tool_xml":
                    if tool_xml is None:
                        # XML linter and non-XML tool, skip for now
                        continue
                    else:
                        lint_context.lint(name, value, tool_xml)
                else:
                    lint_context.lint(name, value, tool_source)


def lint_xml_with(lint_context, tool_xml, extra_modules=None):
    extra_modules = extra_modules or []
    tool_source = get_tool_source(xml_tree=tool_xml)
    return lint_tool_source_with(lint_context, tool_source, extra_modules=extra_modules)


class LintMessage:
    """
    a message from the linter
    """
    def __init__(self, level, message, line, fname, xpath=None):
        self.level = level
        self.message = message
        self.line = line  # 1 based
        self.fname = fname
        self.xpath = xpath

    def __str__(self):
        rval = f".. {self.level.upper()}: {self.message}"
        if self.line is not None:
            rval += " ("
            if self.fname:
                rval += f"{self.fname}:"
            rval += str(self.line)
            rval += ")"
        if self.xpath is not None:
            rval += f" [{self.xpath}]"
        return rval


# TODO: Nothing inherently tool-y about LintContext and in fact
# it is reused for repositories in planemo. Therefore, it should probably
# be moved to galaxy.util.lint.
class LintContext:

    def __init__(self, level, skip_types=None, object_name=None):
        self.skip_types = skip_types or []
        self.level = level
        self.object_name = object_name
        self.found_errors = False
        self.found_warns = False
        self.message_list = []

    def lint(self, name, lint_func, lint_target):
        name = name.replace("tsts", "tests")[len("lint_"):]
        if name in self.skip_types:
            return
        self.printed_linter_info = False
        tmp_message_list = list(self.message_list)
        self.message_list = []

        # call linter
        lint_func(lint_target, self)
        # TODO: colorful emoji if in click CLI.
        if self.error_messages:
            status = "FAIL"
        elif self.warn_messages:
            status = "WARNING"
        else:
            status = "CHECK"

        def print_linter_info():
            if self.printed_linter_info:
                return
            self.printed_linter_info = True
            print(f"Applying linter {name}... {status}")

        for message in self.message_list:
            if message.level != "error":
                continue
            self.found_errors = True
            print_linter_info()
            print(f"{message}")

        if self.level != LEVEL_ERROR:
            for message in self.message_list:
                if message.level != "warning":
                    continue
                self.found_warns = True
                print_linter_info()
                print(f"{message}")

        if self.level == LEVEL_ALL:
            for message in self.message_list:
                if message.level != "info":
                    continue
                print_linter_info()
                print(f"{message}")
            for message in self.message_list:
                if message.level != "check":
                    continue
                print_linter_info()
                print(f"{message}")
        self.message_list = tmp_message_list + self.message_list

    @property
    def valid_messages(self):
        return [x.message for x in self.message_list if x.level == "check"]

    @property
    def info_messages(self):
        return [x.message for x in self.message_list if x.level == "info"]

    @property
    def warn_messages(self):
        return [x.message for x in self.message_list if x.level == "warning"]

    @property
    def error_messages(self):
        return [x.message for x in self.message_list if x.level == "error"]

    def __handle_message(self, level, message, line, fname, xpath, *args):
        if args:
            message = message % args
        self.message_list.append(LintMessage(level=level, message=message,
                                 line=line, fname=fname, xpath=xpath))

    def valid(self, message, line=None, fname=None, xpath=None, *args):
        self.__handle_message("check", message, line, fname, xpath, *args)

    def info(self, message, line=None, fname=None, xpath=None, *args):
        self.__handle_message("info", message, line, fname, xpath, *args)

    def error(self, message, line=None, fname=None, xpath=None, *args):
        self.__handle_message("error", message, line, fname, xpath, *args)

    def warn(self, message, line=None, fname=None, xpath=None, *args):
        self.__handle_message("warning", message, line, fname, xpath, *args)

    def failed(self, fail_level):
        found_warns = self.found_warns
        found_errors = self.found_errors
        if fail_level == LEVEL_WARN:
            lint_fail = (found_warns or found_errors)
        else:
            lint_fail = found_errors
        return lint_fail
