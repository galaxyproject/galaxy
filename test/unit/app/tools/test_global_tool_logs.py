from typing import (
    cast,
    TYPE_CHECKING,
)

import pytest

from galaxy.tools.evaluation import (
    global_tool_logs,
    ToolTemplatingException,
)
from galaxy.tools.expressions import (
    do_eval,
    ExpressionTemplateError,
)
from galaxy.util.bunch import Bunch

if TYPE_CHECKING:
    from galaxy.tools import Tool

FAILING_EXPRESSION = "cat '$(inputs.x.elements[0].path)' > out.txt"
TOOL = cast("Tool", Bunch(id="expression_tool", version="1.0", is_latest_version=True))


def _build_command_line(**kwds) -> None:
    global_tool_logs(lambda: do_eval(FAILING_EXPRESSION, {"x": []}, **kwds), None, "Building Command Line", TOOL)


def test_expression_error_is_reported():
    with pytest.raises(ExpressionTemplateError, match="TypeError: cannot read property '0' of undefined"):
        _build_command_line()


def test_expression_worker_failure_stays_internal():
    with pytest.raises(ToolTemplatingException):
        _build_command_line(sandbox_command=["/nonexistent/jail/binary"])
