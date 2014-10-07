from __future__ import print_function
import inspect
from galaxy.util import submodules

LEVEL_ALL = "all"
LEVEL_WARN = "warn"
LEVEL_ERROR = "error"


def lint_xml(tool_xml, level=LEVEL_ALL, fail_level=LEVEL_WARN):
    import galaxy.tools.linters
    lint_context = LintContext(level=level)
    linter_modules = submodules.submodules(galaxy.tools.linters)
    for module in linter_modules:
        for (name, value) in inspect.getmembers(module):
            if callable(value) and name.startswith("lint_"):
                lint_context.lint(module, name, value, tool_xml)
    found_warns = lint_context.found_warns
    found_errors = lint_context.found_errors
    if level == LEVEL_WARN and (found_warns or found_errors):
        return False
    else:
        return found_errors


class LintContext(object):

    def __init__(self, level):
        self.level = level
        self.found_errors = False
        self.found_warns = False

    def lint(self, module, name, lint_func, tool_xml):
        self.printed_linter_info = False
        self.valid_messages = []
        self.info_messages = []
        self.warn_messages = []
        self.error_messages = []
        lint_func(tool_xml, self)
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
            print("Applying linter %s... %s" % (name, status))

        for message in self.error_messages:
            self.found_errors = True
            print_linter_info()
            print(".. ERROR: %s" % message)

        if self.level != LEVEL_ERROR:
            for message in self.warn_messages:
                self.found_warns = True
                print_linter_info()
                print(".. WARNING: %s" % message)

        if self.level == LEVEL_ALL:
            for message in self.info_messages:
                print_linter_info()
                print(".. INFO: %s" % message)
            for message in self.valid_messages:
                print_linter_info()
                print(".. CHECK: %s" % message)

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
