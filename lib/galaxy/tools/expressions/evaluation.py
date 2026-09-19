from collections.abc import Sequence
from typing import (
    cast,
    Optional,
)

from cwl_utils.expression import do_eval as _do_eval
from cwl_utils.types import (
    CWLObjectType,
    CWLOutputType,
)

from galaxy.tool_util_models.tool_source import JavascriptRequirement
from .js_engine import (
    build_evaluate_program,
    evaluate_program,
    register,
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
