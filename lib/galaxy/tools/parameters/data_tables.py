"""Inspect declared data table usage without deserializing dataset parameters."""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


def _has_selection(value: Any) -> bool:
    if value is None or value == "":
        return False
    if isinstance(value, list):
        return any(_has_selection(item) for item in value)
    if isinstance(value, dict):
        if value.get("src") in ("hda", "ldda", "hdca", "dce", "CollectionAdapter"):
            # A history/data-library reference bundle does not use an installed table entry.
            return False
        if value.get("__class__") == "UnvalidatedValue":
            return _has_selection(value["value"])
        if value.get("__class__") == "NoReplacement":
            return False
        raise ValueError("Unresolved data table parameter value")
    if not isinstance(value, (str, int, float, bool)):
        raise ValueError("Invalid data table parameter value")
    return True


def _from_data_table(parameter: Any) -> bool:
    options = getattr(parameter, "options", None)
    return bool(options is not None and getattr(options, "tool_data_table_name", None))


@dataclass(frozen=True)
class _Input:
    parameter: Any
    table: bool = False
    children: tuple["_Input", ...] = ()
    cases: tuple[tuple["_Input", ...], ...] = ()

    def is_using(self, values: Mapping[str, Any]) -> bool:
        parameter = self.parameter
        value = values.get(parameter.name)
        if parameter.type == "conditional":
            if value is None:
                return False
            if not isinstance(value, dict):
                raise ValueError(f"Invalid conditional state for {parameter.name}")
            test = parameter.test_param
            if test.name not in value:
                raise ValueError(f"Missing conditional selector for {parameter.name}")
            selected = value[test.name]
            if isinstance(selected, dict) and selected.get("__class__") == "UnvalidatedValue":
                selected = selected["value"]
            # Recompute from the selector, as Galaxy does during deserialization;
            # a persisted __current_case__ can be stale after a tool update.
            case = parameter.get_current_case(selected)
            if self.table and _has_selection(selected):
                return True
            return any(child.is_using(value) for child in self.cases[case])
        if parameter.type in ("repeat", "upload_dataset"):
            if value is None:
                return False
            if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
                raise ValueError(f"Invalid repeat state for {parameter.name}")
            return any(child.is_using(item) for item in value for child in self.children)
        if parameter.type == "section":
            if value is None:
                return False
            if not isinstance(value, dict):
                raise ValueError(f"Invalid section state for {parameter.name}")
            return any(child.is_using(value) for child in self.children)
        return _has_selection(value)


def _compile(inputs: Mapping[str, Any]) -> tuple[_Input, ...]:
    relevant = []
    for parameter in inputs.values():
        if parameter.type == "conditional":
            cases = tuple(_compile(case.inputs) for case in parameter.cases)
            table = _from_data_table(parameter.test_param)
            if table or any(cases):
                relevant.append(_Input(parameter, table=table, cases=cases))
        elif parameter.type in ("repeat", "upload_dataset", "section"):
            children = _compile(parameter.inputs)
            if children:
                relevant.append(_Input(parameter, children=children))
        elif _from_data_table(parameter):
            relevant.append(_Input(parameter, table=True))
    return tuple(relevant)


class DataTableParameters:
    """A pruned parameter tree, reusable for every job of one tool instance.

    Usage means a populated ``from_data_table`` select in the active tool state,
    excluding dataset references. It does not inspect templates, evaluate option
    filters, verify table membership, or prove that execution reads an index file.
    """

    def __init__(self, inputs: Mapping[str, Any]):
        self._inputs = _compile(inputs)

    @property
    def has_data_table(self) -> bool:
        return bool(self._inputs)

    def is_using_data_table(self, raw_parameters: Mapping[str, str | None]) -> bool:
        """Decode only relevant top-level values from ``Job.raw_param_dict()``.

        Invalid relevant JSON/state raises instead of reporting that no table is used.
        """
        for input in self._inputs:
            name = input.parameter.name
            raw = raw_parameters.get(name)
            value = json.loads(raw) if raw is not None else None
            if input.is_using({name: value}):
                return True
        return False
