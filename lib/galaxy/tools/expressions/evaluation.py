from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from cwl_utils.expression import do_eval as _do_eval

from .js_engine import (
    build_evaluate_program,
    evaluate_program,
    register,
)

if TYPE_CHECKING:
    from cwl_utils.types import (
        CWLObjectType,
        CWLOutputType,
    )


def do_eval(
    expression: str,
    jobinput: CWLObjectType,
    context: CWLOutputType | None = None,
    sandbox_command: Sequence[str] | None = None,
):
    register()
    return _do_eval(
        expression,
        jobinput,
        [{"class": "InlineJavascriptRequirement"}],
        None,
        None,
        {},
        context=context,
        cwlVersion="v1.2.1",
        sandbox_command=sandbox_command,
    )


def evaluate(config, input):
    # Keep config for backwards compatibility; evaluations use the QuickJS worker.
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

    return evaluate_program(build_evaluate_program(new_input))
