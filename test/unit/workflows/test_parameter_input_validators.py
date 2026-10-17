import json
from typing import Any

from galaxy import model
from galaxy.tools.parameters.workflow_utils import workflow_building_modes
from galaxy.workflow import modules
from .workflow_support import MockTrans

REGEX = {"type": "regex", "expression": "^good", "message": "must start with good", "negate": False}
RANGE = {"type": "in_range", "min": 1, "max": 5, "negate": False}


def import_input(parameter_type, validators):
    """Build a parameter input the way workflow import does and return the saved step."""
    trans = _trans()
    tool_state = {"parameter_type": parameter_type, "optional": False, "validators": validators}
    module = modules.module_factory.from_dict(
        trans, {"type": "parameter_input", "label": "p", "tool_state": json.dumps(tool_state)}
    )
    step = model.WorkflowStep()
    module.save_to_step(step)
    return step


def editor_resave(step, changes=None, drop_prefix=None):
    """Load ``step`` in the editor, submit its form (with ``changes``), and save it again."""
    trans = _trans(workflow_building_modes.ENABLED)
    loaded = modules.module_factory.from_workflow_step(trans, step)
    incoming = dict(_form_values(loaded.get_config_form()["inputs"]))
    if drop_prefix:
        incoming = {key: value for key, value in incoming.items() if not key.startswith(drop_prefix)}
    incoming.update(changes or {})
    edited = modules.module_factory.from_dict(trans, {"type": "parameter_input"}, from_tool_form=True)
    errors: dict[str, Any] = {}
    tool_state = edited.populate_state_from_tool_form(incoming, errors)
    assert not errors, errors
    saved = modules.module_factory.from_dict(
        trans, {"type": "parameter_input", "label": "p", "tool_state": tool_state}, from_tool_form=True
    )
    resaved = model.WorkflowStep()
    saved.save_to_step(resaved)
    return resaved


def runtime_input(step):
    module = modules.module_factory.from_workflow_step(_trans(), step)
    return module.get_runtime_inputs(step)["input"]


def test_regex_validator_survives_import():
    step = import_input("text", [REGEX])
    assert step.tool_inputs["validators"] == [REGEX]


def test_range_validator_survives_import():
    step = import_input("integer", [RANGE])
    assert step.tool_inputs["validators"] == [RANGE]


def test_editor_resave_keeps_regex_validators():
    step = import_input("text", [REGEX])
    assert editor_resave(step).tool_inputs["validators"] == [REGEX]


def test_editor_resave_keeps_range_validator():
    step = import_input("integer", [RANGE])
    assert editor_resave(step).tool_inputs["validators"] == [RANGE]


def test_editor_removes_regex_row():
    step = import_input("text", [REGEX])
    resaved = editor_resave(step, drop_prefix="parameter_definition|validators_")
    assert resaved.tool_inputs["validators"] == []


def test_editor_changes_range_max():
    step = import_input("integer", [RANGE])
    resaved = editor_resave(step, {"parameter_definition|max": 10})
    assert resaved.tool_inputs["validators"] == [{**RANGE, "max": 10}]


def test_stored_min_greater_than_max_still_loads():
    step = model.WorkflowStep()
    step.type = "parameter_input"
    step.tool_inputs = {
        "parameter_type": "integer",
        "optional": False,
        "validators": [{"type": "in_range", "min": 5, "max": 1, "negate": False}],
    }
    module = modules.module_factory.from_workflow_step(_trans(), step)
    assert module.get_export_state()["validators"] == step.tool_inputs["validators"]


def _trans(mode=workflow_building_modes.DISABLED):
    trans = MockTrans()
    trans.workflow_building_mode = mode
    return trans


def _form_values(inputs, prefix=""):
    """Flatten a config form into the ``|``-joined values the client submits (see ``visitInputs``)."""
    for field in inputs:
        name = f"{prefix}|{field['name']}" if prefix else field["name"]
        if field["type"] == "conditional":
            test_param = field["test_param"]
            yield f"{name}|{test_param['name']}", test_param["value"]
            for case in field["cases"]:
                if str(case["value"]) == str(test_param["value"]):
                    yield from _form_values(case["inputs"], name)
        elif field["type"] == "repeat":
            for index, cache in enumerate(field["cache"]):
                yield from _form_values(cache, f"{name}_{index}")
        elif field["type"] == "section":
            yield from _form_values(field["inputs"], name)
        else:
            yield name, field["value"]
