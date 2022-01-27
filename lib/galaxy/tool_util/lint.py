"""This modules contains the functions that drive the tool linting framework."""

import inspect
from typing import (
    Callable,
    List,
    NoReturn,
    Optional,
    TypeVar,
    Union
)

from galaxy.tool_util.parser import get_tool_source
from galaxy.util import submodules


LEVEL_ALL = "all"
LEVEL_WARN = "warn"
LEVEL_ERROR = "error"


class LintMessage:
    """
    a message from the linter
    """
    def __init__(self, level: str, message: str, line, fname, xpath=None):
        self.level = level
        self.message = message
        self.line = line  # 1 based
        self.fname = fname
        self.xpath = xpath

    def __eq__(self, other: Union[str, 'LintMessage']) -> bool:
        """
        add equal operator to easy lookup of a message in a
        List[LintMessage] which is usefull in tests
        """
        if isinstance(other, str):
            return self.message == other
        if isinstance(other, LintMessage):
            return self.message == other.message
        return False

    def __str__(self) -> str:
        return f".. {self.level.upper()}: {self.message}"

    def __repr__(self) -> str:
        return f"LintMessage({self.message})"

    def pretty_print(self, level: bool = True, fname: bool = True, xpath: bool = False) -> str:
        rval = ""
        if level:
            rval += f".. {self.level.upper()}: "
        rval += "{self.message}"
        if fname and self.line is not None:
            rval += " ("
            if self.fname:
                rval += f"{self.fname}:"
            rval += str(self.line)
            rval += ")"
        if xpath and self.xpath is not None:
            rval += f" [{self.xpath}]"
        return rval


LintTargetType = TypeVar('LintTarget')


# TODO: Nothing inherently tool-y about LintContext and in fact
# it is reused for repositories in planemo. Therefore, it should probably
# be moved to galaxy.util.lint.
class LintContext:

    def __init__(self, level: str, skip_types: Optional[List[str]] = None, object_name: Optional[str] = None):
        self.skip_types: List[str] = skip_types or []
        self.level: str = level
        self.object_name: str = object_name
        self.message_list: List[LintMessage] = []

    @property
    def found_errors(self) -> bool:
        return len(self.error_messages) > 0

    @property
    def found_warns(self) -> bool:
        return len(self.warn_messages) > 0

    def lint(self,
             name: str,
             lint_func: Callable[['LintContext', LintTargetType], NoReturn],
             lint_target: LintTargetType,
             silent: bool = False):
        name = name.replace("tsts", "tests")[len("lint_"):]
        if name in self.skip_types:
            return

        if not silent:
            # this is a relict from the past where the lint context
            # was reset when called with a new lint_func, as workaround
            # we safe the message list, apply the lint_func (which then
            # adds to the message_list) and restore the message list
            # at the end (+ append the new messages)
            tmp_message_list = list(self.message_list)
            self.message_list = []

        # call linter
        lint_func(lint_target, self)

        if not silent:
            # TODO: colorful emoji if in click CLI.
            if self.error_messages:
                status = "FAIL"
            elif self.warn_messages:
                status = "WARNING"
            else:
                status = "CHECK"

            def print_linter_info(printed_linter_info):
                if printed_linter_info:
                    return True
                print(f"Applying linter {name}... {status}")
                return True

            plf = False
            for message in self.error_messages:
                plf = print_linter_info(plf)
                print(f"{message}")

            if self.level != LEVEL_ERROR:
                for message in self.warn_messages:
                    plf = print_linter_info(plf)
                    print(f"{message}")

            if self.level == LEVEL_ALL:
                for message in self.info_messages:
                    plf = print_linter_info(plf)
                    print(f"{message}")
                for message in self.valid_messages:
                    plf = print_linter_info(plf)
                    print(f"{message}")
            self.message_list = tmp_message_list + self.message_list

    @property
    def valid_messages(self) -> List[LintMessage]:
        return [x for x in self.message_list if x.level == "check"]

    @property
    def info_messages(self) -> List[LintMessage]:
        return [x for x in self.message_list if x.level == "info"]

    @property
    def warn_messages(self) -> List[LintMessage]:
        return [x for x in self.message_list if x.level == "warning"]

    @property
    def error_messages(self) -> List[LintMessage]:
        return [x for x in self.message_list if x.level == "error"]

    def __handle_message(self, level: str, message: str, line: int, fname: str, xpath: str, *args) -> NoReturn:
        if args:
            message = message % args
        self.message_list.append(LintMessage(level=level, message=message,
                                 line=line, fname=fname, xpath=xpath))

    def valid(self, message: str, line: Optional[str] = None, fname: Optional[str] = None, xpath: Optional[str] = None, *args) -> NoReturn:
        self.__handle_message("check", message, line, fname, xpath, *args)

    def info(self, message: str, line: Optional[str] = None, fname: Optional[str] = None, xpath: Optional[str] = None, *args) -> NoReturn:
        self.__handle_message("info", message, line, fname, xpath, *args)

    def error(self, message: str, line: Optional[str] = None, fname: Optional[str] = None, xpath: Optional[str] = None, *args) -> NoReturn:
        self.__handle_message("error", message, line, fname, xpath, *args)

    def warn(self, message: str, line: Optional[str] = None, fname: Optional[str] = None, xpath: Optional[str] = None, *args) -> NoReturn:
        self.__handle_message("warning", message, line, fname, xpath, *args)

    def failed(self, fail_level: str) -> bool:
        found_warns = self.found_warns
        found_errors = self.found_errors
        if fail_level == LEVEL_WARN:
            lint_fail = (found_warns or found_errors)
        else:
            lint_fail = found_errors
        return lint_fail


def lint_tool_source(tool_source, level=LEVEL_ALL, fail_level=LEVEL_WARN, extra_modules=None, skip_types=None, name=None) -> bool:
    """
    apply all (applicable) linters from the linters submodule
    and the ones in extramodules

    immediately print linter messages (wrt level) and return if linting failed (wrt fail_level)
    """
    extra_modules = extra_modules or []
    skip_types = skip_types or []
    lint_context = LintContext(level=level, skip_types=skip_types, object_name=name)
    lint_tool_source_with(lint_context, tool_source, extra_modules)
    return not lint_context.failed(fail_level)


def get_lint_context_for_tool_source(tool_source, extra_modules=None, skip_types=None, name=None) -> LintContext:
    """
    this is the silent variant of lint_tool_source
    it returns the LintContext from which all linter messages
    and the status can be obtained
    """
    extra_modules = extra_modules or []
    skip_types = skip_types or []
    lint_context = LintContext(level="all", skip_types=skip_types, object_name=name)
    lint_tool_source_with(lint_context, tool_source, extra_modules, silent=True)
    return lint_context


def lint_xml(tool_xml, level=LEVEL_ALL, fail_level=LEVEL_WARN, extra_modules=None, skip_types=None, name=None) -> bool:
    """
    silently lint an xml tool
    """
    extra_modules = extra_modules or []
    skip_types = skip_types or []
    lint_context = LintContext(level=level, skip_types=skip_types, object_name=name)
    lint_xml_with(lint_context, tool_xml, extra_modules)

    return not lint_context.failed(fail_level)


def lint_tool_source_with(lint_context, tool_source, extra_modules=None, silent=False) -> LintContext:
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
                        lint_context.lint(name, value, tool_xml, silent)
                else:
                    lint_context.lint(name, value, tool_source, silent)
    return lint_context


def lint_xml_with(lint_context, tool_xml, extra_modules=None) -> LintContext:
    extra_modules = extra_modules or []
    tool_source = get_tool_source(xml_tree=tool_xml)
    return lint_tool_source_with(lint_context, tool_source, extra_modules=extra_modules)
