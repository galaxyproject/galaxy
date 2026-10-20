"""Inspect declared data table usage without deserializing dataset parameters."""

import json
from collections.abc import (
    Iterator,
    Mapping,
)
from contextlib import suppress
from typing import Any

from galaxy.tools.parameters import visit_input_values
from galaxy.tools.parameters.basic import SelectToolParameter
from galaxy.tools.parameters.grouping import (
    Conditional,
    Repeat,
    Section,
    UploadDataset,
)


def is_data_table_select(parameter: Any) -> bool:
    """Whether ``parameter`` is a select whose options come from ``from_data_table``."""
    options = getattr(parameter, "options", None)
    return isinstance(parameter, SelectToolParameter) and bool(getattr(options, "tool_data_table_name", None))


def conditional_selectors(inputs: Mapping[str, Any]) -> Iterator[Any]:
    """Conditional test parameters, which ``Tool.input_params`` does not include."""
    for input in inputs.values():
        if isinstance(input, Conditional):
            yield input.test_param
            for case in input.cases:
                yield from conditional_selectors(case.inputs or {})
        elif isinstance(input, (Repeat, Section, UploadDataset)):
            yield from conditional_selectors(input.inputs or {})


def _has_selection(value: Any) -> bool:
    if isinstance(value, list):
        return any(_has_selection(item) for item in value)
    # Dicts are history datasets offered as table entries, runtime or
    # NoReplacement values; none of them select an installed table entry.
    return not isinstance(value, dict) and value not in (None, "")


def uses_data_table(inputs: Mapping[str, Any], raw_parameters: Mapping[str, str | None]) -> bool:
    """Whether a populated ``from_data_table`` select is part of the active state.

    ``raw_parameters`` is ``Job.raw_param_dict()``. Values are only JSON-decoded,
    so dataset references are never loaded.
    """
    used = False

    def visitor(input: Any, value: Any, **kwargs: Any) -> None:
        nonlocal used
        used = used or (is_data_table_select(input) and _has_selection(value))

    for name, input in inputs.items():
        raw = raw_parameters.get(name)
        if raw is None:
            continue
        # Like params_from_strings(ignore_errors=True) in the job wrapper, skip
        # state that no longer matches the tool instead of failing the job.
        with suppress(Exception):
            visit_input_values({name: input}, {name: json.loads(raw)}, visitor)
        if used:
            return True
    return False
