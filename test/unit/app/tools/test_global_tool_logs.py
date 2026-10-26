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


def _tool(tool_type: str = "default", expose_dataset_path: bool = False) -> "Tool":
    return cast(
        "Tool",
        Bunch(
            id="expression_tool",
            version="1.0",
            is_latest_version=True,
            tool_type=tool_type,
            app=Bunch(config=Bunch(expose_dataset_path=expose_dataset_path)),
        ),
    )


def _build_command_line(tool: "Tool", **kwds) -> None:
    global_tool_logs(lambda: do_eval(FAILING_EXPRESSION, {"x": []}, **kwds), None, "Building Command Line", tool)


def test_user_defined_tool_reports_expression_error():
    with pytest.raises(ExpressionTemplateError) as exc:
        _build_command_line(_tool("user_defined"))
    assert str(exc.value) == (
        "Error occurred while building command line for tool 'expression_tool': "
        "TypeError: cannot read property '0' of undefined"
    )


def test_expression_error_needs_expose_dataset_path():
    with pytest.raises(ToolTemplatingException) as exc:
        _build_command_line(_tool())
    assert str(exc.value) == "Error occurred while building command line for tool 'expression_tool'"


def test_expose_dataset_path_reports_expression_error():
    with pytest.raises(ExpressionTemplateError, match="TypeError: cannot read property '0' of undefined"):
        _build_command_line(_tool(expose_dataset_path=True))


def test_expression_worker_failure_stays_internal():
    with pytest.raises(ToolTemplatingException):
        _build_command_line(_tool("user_defined"), sandbox_command=["/nonexistent/jail/binary"])
