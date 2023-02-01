"""This modules contains the functions that drive the tool linting framework.

LintContext: a container for LintMessages
LintMessage: the actual message and level

The idea is to define a LintContext and to apply a linting function ``foo`` on a
``target``. The ``level`` (defined by ``LintLevel``) determines which linting
messages are shown::


    lint_ctx = LintContext(level) # level is the reporting level
    lint_ctx.lint(..., lint_func = foo, lint_target = target, ...)

The ``lint`` function essentially calls ``foo(target, self)``. Hence
the function ``foo`` must have two parameters:

1. the object to lint
2. the lint context

In ``foo`` the lint context can be used to add LintMessages to the lint context
by using its ``valid``, ``info``, ``warn``, and ``error`` functions::


    lint_foo(target, lint_ctx):
        lint_ctx.error("target is screwed")

Calling ``lint`` prints out the messages emmited by the linter
function immediately. Which messages are shown can be determined with the
``level`` argument of the ``LintContext`` constructor. If set to ``SILENT``,
no messages will be printed.

For special lint targets it might be useful to have additional information
in the lint messages. This can be achieved by subclassing ``LintMessage``.
See for instance ``XMLLintMessageLine`` which has an additional argument
``node`` in its constructor which is used to determine the line and filename in
an XML document that caused the message.

In order to use this.

- the lint context needs to be initialized with the additional parameter
  ``lint_message_class=XMLLintMessageLine``
- the additional parameter needs to be added as well to calls adding messages
  to the lint context, e.g. ``lint_ctx.error("some message", node=X)``. Note
  that the additional properties must be given as keyword arguments.
"""

import inspect
from enum import IntEnum
from typing import (
    Callable,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
)

from galaxy.tool_util.parser import get_tool_source
from galaxy.util import (
    etree,
    submodules,
)


class LintLevel(IntEnum):
    SILENT = 5
    ERROR = 4
    WARN = 3
    INFO = 2
    VALID = 1
    ALL = 0


class LintMessage:
    """
    a message from the linter
    """

    def __init__(self, level: str, message: str, **kwargs):
        self.level = level
        self.message = message

    def __eq__(self, other) -> bool:
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


class XMLLintMessageLine(LintMessage):
    def __init__(self, level: str, message: str, node: Optional[etree.Element] = None):
        super().__init__(level, message)
        self.line = None
        if node is not None:
            self.line = node.sourceline

    def __str__(self) -> str:
        rval = super().__str__()
        if self.line is not None:
            rval += " ("
            rval += str(self.line)
            rval += ")"
        return rval


class XMLLintMessageXPath(LintMessage):
    def __init__(self, level: str, message: str, node: Optional[etree.Element] = None):
        super().__init__(level, message)
        self.xpath = None
        if node is not None:
            tool_xml = node.getroottree()
            self.xpath = tool_xml.getpath(node)

    def __str__(self) -> str:
        rval = super().__str__()
        if self.xpath is not None:
            rval += f" [{self.xpath}]"
        return rval


LintTargetType = TypeVar("LintTargetType")


# TODO: Nothing inherently tool-y about LintContext and in fact
# it is reused for repositories in planemo. Therefore, it should probably
# be moved to galaxy.util.lint.
class LintContext:
    skip_types: List[str]
    level: LintLevel
    lint_message_class: Type[LintMessage]
    object_name: Optional[str]
    message_list: List[LintMessage]

    def __init__(
        self,
        level: Union[LintLevel, str],
        lint_message_class: Type[LintMessage] = LintMessage,
        skip_types: Optional[List[str]] = None,
        object_name: Optional[str] = None,
    ):
        self.skip_types = skip_types or []
        if isinstance(level, str):
            self.level = LintLevel[level.upper()]
        else:
            self.level = level
        self.lint_message_class = lint_message_class
        self.object_name = object_name
        self.message_list = []

    @property
    def found_errors(self) -> bool:
        return len(self.error_messages) > 0

    @property
    def found_warns(self) -> bool:
        return len(self.warn_messages) > 0

    def lint(self, name: str, lint_func: Callable[[LintTargetType, "LintContext"], None], lint_target: LintTargetType):
        name = name[len("lint_") :]
        if name in self.skip_types:
            return

        if self.level < LintLevel.SILENT:
            # this is a relict from the past where the lint context
            # was reset when called with a new lint_func, as workaround
            # we save the message list, apply the lint_func (which then
            # adds to the message_list) and restore the message list
            # at the end (+ append the new messages)
            tmp_message_list = list(self.message_list)
            self.message_list = []

        # call linter
        lint_func(lint_target, self)

        if self.level < LintLevel.SILENT:
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

            if self.level <= LintLevel.WARN:
                for message in self.warn_messages:
                    plf = print_linter_info(plf)
                    print(f"{message}")

            if self.level <= LintLevel.INFO:
                for message in self.info_messages:
                    plf = print_linter_info(plf)
                    print(f"{message}")
            if self.level <= LintLevel.VALID:
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

    def __handle_message(self, level: str, message: str, *args, **kwargs) -> None:
        if args:
            message = message % args
        self.message_list.append(self.lint_message_class(level=level, message=message, **kwargs))

    def valid(self, message: str, *args, **kwargs) -> None:
        self.__handle_message("check", message, *args, **kwargs)

    def info(self, message: str, *args, **kwargs) -> None:
        self.__handle_message("info", message, *args, **kwargs)

    def error(self, message: str, *args, **kwargs) -> None:
        self.__handle_message("error", message, *args, **kwargs)

    def warn(self, message: str, *args, **kwargs) -> None:
        self.__handle_message("warning", message, *args, **kwargs)

    def failed(self, fail_level: Union[LintLevel, str]) -> bool:
        if isinstance(fail_level, str):
            fail_level = LintLevel[fail_level.upper()]
        found_warns = self.found_warns
        found_errors = self.found_errors
        if fail_level == LintLevel.WARN:
            lint_fail = found_warns or found_errors
        elif fail_level >= LintLevel.ERROR:
            lint_fail = found_errors
        return lint_fail


def lint_tool_source(
    tool_source, level=LintLevel.ALL, fail_level=LintLevel.WARN, extra_modules=None, skip_types=None, name=None
) -> bool:
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
    lint_context = LintContext(level=LintLevel.SILENT, skip_types=skip_types, object_name=name)
    lint_tool_source_with(lint_context, tool_source, extra_modules)
    return lint_context


def lint_xml(
    tool_xml,
    level=LintLevel.ALL,
    fail_level=LintLevel.WARN,
    lint_message_class=LintMessage,
    extra_modules=None,
    skip_types=None,
    name=None,
) -> bool:
    """
    lint an xml tool
    """
    extra_modules = extra_modules or []
    skip_types = skip_types or []
    lint_context = LintContext(
        level=level, lint_message_class=lint_message_class, skip_types=skip_types, object_name=name
    )
    lint_xml_with(lint_context, tool_xml, extra_modules)

    return not lint_context.failed(fail_level)


def lint_tool_source_with(lint_context, tool_source, extra_modules=None) -> LintContext:
    extra_modules = extra_modules or []
    import galaxy.tool_util.linters

    tool_xml = getattr(tool_source, "xml_tree", None)
    tool_type = tool_source.parse_tool_type() or "default"
    linter_modules = submodules.import_submodules(galaxy.tool_util.linters)
    linter_modules.extend(extra_modules)
    for module in linter_modules:
        lint_tool_types = getattr(module, "lint_tool_types", ["default", "manage_data"])
        if not ("*" in lint_tool_types or tool_type in lint_tool_types):
            continue

        for name, value in inspect.getmembers(module):
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
    return lint_context


def lint_xml_with(lint_context, tool_xml, extra_modules=None) -> LintContext:
    extra_modules = extra_modules or []
    tool_source = get_tool_source(xml_tree=tool_xml)
    return lint_tool_source_with(lint_context, tool_source, extra_modules=extra_modules)
