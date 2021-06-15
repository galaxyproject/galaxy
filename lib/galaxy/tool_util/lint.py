"""This modules contains the functions that drive the tool linting framework."""

import inspect

from galaxy.tool_util.parser import get_tool_source
from galaxy.util import submodules
from galaxy.util.getargspec import getfullargspec


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
                first_arg = getfullargspec(value).args[0]
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

    def lint(self, name, lint_func, lint_target):
        name = name.replace("tsts", "tests")[len("lint_"):]
        if name in self.skip_types:
            return
        self.printed_linter_info = False
        self.valid_messages = []
        self.info_messages = []
        self.warn_messages = []
        self.error_messages = []
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

        for message in self.error_messages:
            self.found_errors = True
            print_linter_info()
            print(f".. ERROR: {message}")

        if self.level != LEVEL_ERROR:
            for message in self.warn_messages:
                self.found_warns = True
                print_linter_info()
                print(f".. WARNING: {message}")

        if self.level == LEVEL_ALL:
            for message in self.info_messages:
                print_linter_info()
                print(f".. INFO: {message}")
            for message in self.valid_messages:
                print_linter_info()
                print(f".. CHECK: {message}")

    def __handle_message(self, message_list, message, *args):
        if args:
            message = message % args
        message_list.append(message)

    def valid(self, message, *args):
        self.__handle_message(self.valid_messages, message, *args)

    def info(self, message, *args):
        self.__handle_message(self.info_messages, message, *args)

    def error(self, message, *args):
        self.__handle_message(self.error_messages, message, *args)

    def warn(self, message, *args):
        self.__handle_message(self.warn_messages, message, *args)

    def failed(self, fail_level):
        found_warns = self.found_warns
        found_errors = self.found_errors
        if fail_level == LEVEL_WARN:
            lint_fail = (found_warns or found_errors)
        else:
            lint_fail = found_errors
        return lint_fail
