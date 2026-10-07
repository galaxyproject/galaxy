"""Tool form fields by the parameter paths ``NavigatesGalaxy.tool_form_fill`` takes, read without a browser."""

import re
from typing import (
    Any,
    NamedTuple,
)

REPEAT_PATH = re.compile(r"^(.+?)_(\d+)\|.+$")


class ToolFormParameter(NamedTuple):
    """One tool form field, addressed by the path ``tool_form_fill`` takes."""

    path: str
    label: str
    type: str
    value: Any
    # (label, value) pairs; data options are ("<hid>: <name>", "<hid>").
    options: list[tuple[str, str]]
    # ``<test parameter path>=<case value>`` for fields inside one conditional case.
    condition: str | None = None


def repeat_instance_counts(paths: list[str]) -> dict[str, int]:
    """How many instances of each repeat the paths need, e.g. ``queries_1|input`` needs two ``queries``."""
    counts: dict[str, int] = {}
    for path in paths:
        if match := REPEAT_PATH.match(path):
            name, index = match.group(1), int(match.group(2))
            counts[name] = max(counts.get(name, 0), index + 1)
    return counts


def tool_form_parameters_from_build(
    inputs: list[dict[str, Any]], prefix: str = "", condition: str | None = None
) -> list[ToolFormParameter]:
    """Flatten a tool build model's inputs into form fields, listing every conditional case."""
    parameters: list[ToolFormParameter] = []
    for input in inputs:
        input_type = input["type"]
        path = f"{prefix}{input['name']}"
        if input_type == "conditional":
            test_param = input["test_param"]
            test_path = f"{path}|{test_param['name']}"
            parameters.extend(tool_form_parameters_from_build([test_param], f"{path}|", condition))
            for case in input["cases"]:
                case_condition = f"{test_path}={case['value']}"
                parameters.extend(tool_form_parameters_from_build(case["inputs"], f"{path}|", case_condition))
        elif input_type == "section":
            parameters.extend(tool_form_parameters_from_build(input["inputs"], f"{path}|", condition))
        elif input_type == "repeat":
            instances = input.get("cache") or [input["inputs"]]
            label = input.get("title") or input["name"]
            parameters.append(ToolFormParameter(path, label, "repeat", len(input.get("cache") or []), [], condition))
            for index, instance in enumerate(instances):
                parameters.extend(tool_form_parameters_from_build(instance, f"{path}_{index}|", condition))
        else:
            label = input.get("label") or input["name"]
            options, value = _options_and_value(input)
            parameters.append(ToolFormParameter(path, label, input_type, value, options, condition))
    return parameters


def _options_and_value(input: dict[str, Any]) -> tuple[list[tuple[str, str]], Any]:
    options = input.get("options")
    if input["type"] in ("data", "data_collection") and isinstance(options, dict):
        return _data_options_and_value(options, input.get("pinned") or {}, input.get("value"))
    if isinstance(options, list):
        return _flatten_options(options), input.get("value")
    return [], input.get("value")


def _data_options_and_value(
    options: dict[str, list[dict[str, Any]]], pinned: dict[str, list[dict[str, Any]]], value: Any
) -> tuple[list[tuple[str, str]], Any]:
    def entries(*sources: str) -> list[dict[str, Any]]:
        # Rerun selections outside the options page are in ``pinned``; list them first like the client.
        return [item for source in sources for item in [*pinned.get(source, []), *options.get(source, [])]]

    items = entries("hda", "hdca")
    # Collection elements and library datasets have no usable hid, so only label a selected one by name.
    labels = {(item["src"], item["id"]): item["name"] for item in entries("dce", "ldda")}
    labels.update({(item["src"], item["id"]): f"{item['hid']}: {item['name']}" for item in items})
    selected = [labels.get((v["src"], v["id"]), v["id"]) for v in (value or {}).get("values", [])]
    data_options = [(f"{item['hid']}: {item['name']}", str(item["hid"])) for item in items]
    return data_options, selected[0] if len(selected) == 1 else selected


def _flatten_options(options: list[Any]) -> list[tuple[str, str]]:
    # Select options are [label, value, selected]; drill-down options nest as {name, value, options}.
    flat: list[tuple[str, str]] = []
    for option in options:
        if isinstance(option, dict):
            flat.append((str(option["name"]), str(option["value"])))
            flat.extend(_flatten_options(option.get("options") or []))
        else:
            flat.append((str(option[0]), str(option[1])))
    return flat
