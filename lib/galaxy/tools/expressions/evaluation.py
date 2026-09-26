from collections.abc import Sequence
from typing import (
    cast,
    Optional,
)

from cwl_utils.errors import SubstitutionError
from cwl_utils.expression import (
    do_eval as _do_eval,
    needs_parsing,
    scanner,
)
from cwl_utils.types import (
    CWLObjectType,
    CWLOutputType,
)

from galaxy.exceptions import MessageException
from galaxy.tool_util_models.tool_source import JavascriptRequirement
from .js_engine import (
    build_evaluate_program,
    evaluate_program,
    register,
)

# How much of an unparseable template is quoted back to its author.
TEMPLATE_SNIPPET_LENGTH = 80


class ExpressionTemplateError(MessageException):
    """A ``$(...)``/``${...}`` block in a tool template does not parse."""


def validate_expression_template(expression: str, description: str = "command template") -> None:
    """Reject a template the expression scanner cannot read before evaluating it."""
    if not needs_parsing(expression):
        return
    consumed = len(expression) - len(expression.lstrip())
    scan = expression.strip()
    while True:
        try:
            window = scanner(scan)
        except SubstitutionError as exc:
            raise ExpressionTemplateError(_unterminated_message(expression, scan, consumed, description)) from exc
        if window is None:
            return
        start, end = window
        if scan[start] == "\\" and scan[start : end + 1] in ("\\$(", "\\${"):
            # interpolate() consumes the escaped opener along with the backslash.
            end += 1
        consumed += end
        scan = scan[end:]


def _unterminated_message(expression: str, scan: str, consumed: int, description: str) -> str:
    offsets = [offset for offset in (scan.find("$("), scan.find("${")) if offset >= 0]
    position = consumed + (min(offsets) if offsets else 0)
    line = expression.count("\n", 0, position) + 1
    column = position - expression.rfind("\n", 0, position)
    snippet = expression[position : position + TEMPLATE_SNIPPET_LENGTH]
    if len(expression) > position + TEMPLATE_SNIPPET_LENGTH:
        snippet += "..."
    return (
        f"Unterminated expression in tool {description} at line {line}, column {column}: {snippet!r}. "
        "'$(' opens a Galaxy expression, so the parentheses and quotes inside it have to balance; "
        "write '\\$(' to pass a literal shell command substitution through to the shell."
    )


def do_eval(
    expression: str,
    jobinput: CWLObjectType,
    javascript_requirements: list[JavascriptRequirement] | None = None,
    outdir: str | None = None,
    tmpdir: str | None = None,
    context: Optional["CWLOutputType"] = None,
    sandbox_command: Sequence[str] | None = None,
):
    validate_expression_template(expression)
    # Register the QuickJS worker for cwl_utils JavaScript evaluations.
    # ``sandbox_command`` optionally adds an OS-level jail around the worker.
    register()
    requirements: list[CWLObjectType] = []
    if javascript_requirements:
        for req in javascript_requirements:
            if expression_lib := req.expression_lib:
                requirements.append(
                    {"class": "InlineJavascriptRequirement", "expressionLib": cast(CWLOutputType, expression_lib)}
                )
            else:
                requirements.append({"class": "InlineJavascriptRequirement"})
    else:
        requirements = [{"class": "InlineJavascriptRequirement"}]
    return _do_eval(
        expression,
        jobinput,
        requirements,
        None,
        None,
        {},
        context=context,
        cwlVersion="v1.2.1",
        sandbox_command=sandbox_command,
    )


def evaluate(config, input):
    # ``config`` is retained for backwards compatibility but is no longer used: the
    # expression runs in the Python worker with QuickJS.
    register()

    default_context = {
        "engineConfig": [],
        "job": {},
        "context": None,
        "outdir": None,
        "tmpdir": None,
    }

    new_input = default_context
    new_input.update(input)

    program = build_evaluate_program(new_input)
    return evaluate_program(program)
