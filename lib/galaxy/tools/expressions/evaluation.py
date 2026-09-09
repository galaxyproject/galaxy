from __future__ import annotations

from collections.abc import Sequence
from typing import MutableMapping

from cwl_utils.expression import do_eval as _do_eval

from .js_engine import (
    build_evaluate_program,
    evaluate_program,
    register,
)


def do_eval(expression: str, context: MutableMapping, sandbox_command: Sequence[str] | None = None):
    register()
    return _do_eval(
        expression,
        context,
        [{"class": "InlineJavascriptRequirement"}],
        None,
        None,
        {},
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
