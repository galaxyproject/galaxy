import json
from typing import Any

import pytest

from galaxy import model
from galaxy.exceptions import RequestParameterInvalidException
from galaxy.tools.parameters.workflow_utils import workflow_building_modes
from galaxy.workflow import modules
from .workflow_support import MockTrans

REGEX = {"type": "regex", "expression": "^good", "message": "must start with good", "negate": False}
RANGE = {"type": "in_range", "min": 1, "max": 5, "negate": False}
NEGATED_REGEX = {"type": "regex", "expression": "^bad", "message": "no bad", "negate": True}
NEGATED_RANGE = {"type": "in_range", "min": 1, "max": 5, "negate": True}
MIN_RANGE = {"type": "in_range", "min": 1, "negate": False}
MAX_RANGE = {"type": "in_range", "max": 5, "negate": False}
MESSAGE_RANGE = {"type": "in_range", "min": 1, "max": 5, "message": "1-5 only"}
EXCLUSIVE_RANGE = {"type": "in_range", "min": 1, "max": 5, "exclude_min": True, "negate": False}


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


def editor_resave(step, changes=None, drop_prefix=None, parameter_type=None):
    """Load ``step`` in the editor, submit its form (with ``changes``), and save it again."""
    trans = _trans(workflow_building_modes.ENABLED)
    loaded = modules.module_factory.from_workflow_step(trans, step)
    form_inputs = loaded.get_config_form()["inputs"]
    if parameter_type:
        # as the client does on a type change: submit the newly selected case's fields
        form_inputs[0]["test_param"]["value"] = parameter_type
    incoming = dict(_form_values(form_inputs))
    if drop_prefix:
        incoming = {key: value for key, value in incoming.items() if not key.startswith(drop_prefix)}
    incoming.update(changes or {})
    return _save_form(incoming)


def normalized(validators):
    """Drop unset bounds and false flags, which the editor's min/max fields cannot distinguish."""
    return [
        {key: value for key, value in validator.items() if value is not None and value is not False}
        for validator in validators
    ]


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


@pytest.mark.parametrize(
    "parameter_type,validators,accepted,rejected",
    [
        ("text", [NEGATED_REGEX], "good", "bad1"),
        ("integer", [NEGATED_RANGE], 7, 3),
        ("integer", [MIN_RANGE, MAX_RANGE], 3, 0),
        ("integer", [MIN_RANGE, MAX_RANGE], 3, 7),
        ("integer", [EXCLUSIVE_RANGE], 2, 1),
    ],
)
def test_imported_validators_are_kept(parameter_type, validators, accepted, rejected):
    step = import_input(parameter_type, validators)
    param = runtime_input(step)
    param.validate(accepted, _trans())
    with pytest.raises(ValueError):
        param.validate(rejected, _trans())


def test_imported_range_message_is_kept():
    param = runtime_input(import_input("integer", [MESSAGE_RANGE]))
    with pytest.raises(ValueError, match="1-5 only"):
        param.validate(7, _trans())


@pytest.mark.parametrize(
    "parameter_type,validators",
    [
        ("text", [REGEX, NEGATED_REGEX]),
        ("integer", [NEGATED_RANGE]),
        ("integer", [MIN_RANGE, MAX_RANGE]),
        ("integer", [MESSAGE_RANGE]),
        ("float", [EXCLUSIVE_RANGE]),
        ("text", [{"type": "length", "min": 2, "negate": False}]),
    ],
)
def test_import_stores_and_exports_declared_validators(parameter_type, validators):
    step = import_input(parameter_type, validators)
    assert normalized(step.tool_inputs["validators"]) == normalized(validators)
    export_state = modules.module_factory.from_workflow_step(_trans(), step).get_export_state()
    assert normalized(export_state["validators"]) == normalized(validators)


@pytest.mark.parametrize(
    "parameter_type,validators",
    [
        ("text", [REGEX, NEGATED_REGEX]),
        ("integer", [MIN_RANGE, MAX_RANGE]),
        ("integer", [MESSAGE_RANGE]),
        ("float", [EXCLUSIVE_RANGE]),
    ],
)
def test_editor_resave_keeps_validators_the_form_cannot_show(parameter_type, validators):
    step = import_input(parameter_type, validators)
    assert normalized(editor_resave(step).tool_inputs["validators"]) == normalized(validators)


def test_editor_edits_shown_validators_and_keeps_hidden_ones():
    step = import_input("text", [REGEX, NEGATED_REGEX])
    resaved = editor_resave(step, drop_prefix="parameter_definition|validators_")
    assert resaved.tool_inputs["validators"] == [NEGATED_REGEX]


def test_editor_drops_hidden_validators_when_parameter_type_changes():
    step = import_input("text", [NEGATED_REGEX])
    resaved = editor_resave(step, parameter_type="integer")
    assert resaved.tool_inputs["parameter_type"] == "integer"
    assert resaved.tool_inputs["validators"] == []


@pytest.mark.parametrize(
    "validators",
    [
        [{"type": "in_range", "min": 5, "max": 1}],
        [MIN_RANGE, {"type": "in_range", "min": 5, "max": 1}],
        [{"type": "in_range", "min": "one"}],
        [{"type": "not_a_validator"}],
        [{"type": "length", "min": 5, "max": 1}],
    ],
)
def test_invalid_validators_rejected_at_import(validators):
    with pytest.raises(RequestParameterInvalidException, match="p"):
        import_input("integer", validators)


def test_import_error_names_the_problem():
    with pytest.raises(RequestParameterInvalidException) as exc_info:
        import_input("integer", [{"type": "in_range", "min": 5, "max": 1}])
    assert (
        str(exc_info.value)
        == "Invalid validator on workflow parameter input 'p': min must be less than or equal to max"
    )


def test_validator_spelling_out_defaults_is_shown_in_the_form():
    step = import_input("text", [{**REGEX, "implicit": False}])
    resaved = editor_resave(step, drop_prefix="parameter_definition|validators_")
    assert resaved.tool_inputs["validators"] == []


def test_unsafe_hidden_validator_rejected_at_save():
    unsafe = [{"type": "metadata", "check": ["dbkey"]}]
    with pytest.raises(RequestParameterInvalidException):
        _save_form(
            {
                "parameter_definition|parameter_type": "text",
                "parameter_definition|optional|optional": "false",
                "parameter_definition|extra_validators": json.dumps(unsafe),
            }
        )


def _trans(mode=workflow_building_modes.DISABLED):
    trans = MockTrans()
    trans.workflow_building_mode = mode
    return trans


def _save_form(incoming):
    trans = _trans(workflow_building_modes.ENABLED)
    edited = modules.module_factory.from_dict(trans, {"type": "parameter_input"}, from_tool_form=True)
    errors: dict[str, Any] = {}
    tool_state = edited.populate_state_from_tool_form(incoming, errors)
    assert not errors, errors
    saved = modules.module_factory.from_dict(
        trans, {"type": "parameter_input", "label": "p", "tool_state": tool_state}, from_tool_form=True
    )
    step = model.WorkflowStep()
    saved.save_to_step(step)
    return step


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
