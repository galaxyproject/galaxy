from typing import Any

import pytest

from galaxy.tool_util.toolbox.filters import FilterFactory
from galaxy.util.bunch import Bunch
from galaxy.webapps.galaxy.api.users import UserAPIController


def described_filter(context, tool):
    """Hide selected tools.

    Enable this filter to hide selected tools from the toolbox.
    """
    return False


def undocumented_filter(context, tool):
    return False


def build_inputs(filter_names, saved_values=None):
    base_module, module_name = __name__.rsplit(".", 1)
    config = Bunch(toolbox_filter_base_modules=base_module)
    factory = FilterFactory(Bunch(app=Bunch(config=config)))
    names = [f"{module_name}:{name}" for name in filter_names]
    filter_types = {"toolbox_tool_filters": {"title": "Tools", "config": names}}
    inputs: list[dict[str, Any]] = []
    errors: dict[str, str] = {}
    # Building form inputs does not require application-backed controller state.
    controller = UserAPIController.__new__(UserAPIController)
    controller._add_filter_inputs(factory, filter_types, inputs, errors, "toolbox_tool_filters", saved_values or {})
    return inputs, errors, names


def test_unavailable_filter_is_not_offered():
    inputs, errors, names = build_inputs(["missing_filter"])
    assert inputs == []
    assert errors == {f"toolbox_tool_filters|{names[0]}": "Filter function not found."}


@pytest.mark.parametrize("selected", [False, True])
def test_valid_filter_preserves_description_and_selection(selected):
    module_name = __name__.rsplit(".", 1)[1]
    filter_name = f"{module_name}:described_filter"
    saved_values = {"toolbox_tool_filters": [filter_name]} if selected else {}
    inputs, errors, names = build_inputs(["missing_filter", "described_filter"], saved_values)
    assert errors == {f"toolbox_tool_filters|{names[0]}": "Filter function not found."}
    assert len(inputs) == 1
    assert inputs[0]["inputs"] == [
        {
            "type": "boolean",
            "name": filter_name,
            "label": "Hide selected tools.",
            "help": "Enable this filter to hide selected tools from the toolbox.",
            "value": selected,
        }
    ]


def test_filter_without_docstring_uses_name():
    inputs, errors, names = build_inputs(["undocumented_filter"])
    assert errors == {}
    assert inputs[0]["inputs"][0]["label"] == names[0]
    assert inputs[0]["inputs"][0]["help"] == "No description available."
