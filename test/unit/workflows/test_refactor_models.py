from typing import cast

from galaxy.workflow.refactor.schema import (
    AddInputAction,
    AddStepAction,
    ConnectAction,
    DisconnectAction,
    ExtractInputAction,
    ExtractUntypedParameter,
    InputReferenceByLabel,
    InputReferenceByOrderIndex,
    RefactorActionExecution,
    RefactorActions,
    StepReferenceByLabel,
    StepReferenceByOrderIndex,
    UpdateStepLabelAction,
)


def test_root_list():
    request = {
        "actions": [
            {"action_type": "add_step", "label": "foobar", "type": "tool", "tool_state": {"a": 6}},
            {"action_type": "update_step_label", "label": "new_label", "step": {"order_index": 5}},
            {"action_type": "update_step_label", "label": "new_label", "step": {"label": "cool_label"}},
            {"action_type": "connect", "input": {"input_name": "foobar", "order_index": 6}, "output": {"label": "cow"}},
            {
                "action_type": "disconnect",
                "input": {"input_name": "foobar2", "label": "foolabel"},
                "output": {"order_index": 7, "output_name": "o_name"},
            },
            {"action_type": "add_input", "type": "data"},
            {"action_type": "add_input", "type": "integer", "optional": True, "default": 5},
            {"action_type": "extract_input", "input": {"order_index": 5, "input_name": "foobar"}},
            {"action_type": "extract_untyped_parameter", "name": "foo"},
            {"action_type": "extract_untyped_parameter", "name": "foo", "label": "new_foo"},
        ],
    }
    ar = RefactorActions(**request)
    actions = ar.actions

    a0 = actions[0]
    assert a0.action_type == "add_step"
    a0t = cast(AddStepAction, a0)
    assert a0t.tool_state
    assert a0t.tool_state["a"] == 6
    assert a0t.label == "foobar"

    a1 = actions[1]
    assert a1.action_type == "update_step_label"
    a1t = cast(UpdateStepLabelAction, a1)
    assert isinstance(a1t.step, StepReferenceByOrderIndex)
    assert a1t.step.order_index == 5
    a2t = cast(UpdateStepLabelAction, actions[2])
    assert isinstance(a2t.step, StepReferenceByLabel)
    assert a2t.step.label == "cool_label"

    a3 = actions[3]
    assert a3.action_type == "connect"
    a3t = cast(ConnectAction, a3)
    # Verify it sets default output_name
    assert a3t.output.output_name == "output"
    assert a3t.input.input_name == "foobar"

    a4 = cast(DisconnectAction, actions[4])
    assert a4.output.output_name == "o_name"
    assert isinstance(a4.input, InputReferenceByLabel)
    assert a4.input.input_name == "foobar2"
    assert a4.input.label == "foolabel"

    a5 = cast(AddInputAction, actions[5])
    assert a5.type == "data"
    assert a5.optional is False

    a6 = cast(AddInputAction, actions[6])
    assert a6.optional is True
    assert a6.default == 5

    a7 = cast(ExtractInputAction, actions[7])
    assert isinstance(a7.input, InputReferenceByOrderIndex)
    assert a7.input.order_index == 5
    assert a7.input.input_name == "foobar"

    a8 = cast(ExtractUntypedParameter, actions[8])
    assert a8.name == "foo"
    assert a8.label is None

    a9 = cast(ExtractUntypedParameter, actions[9])
    assert a9.name == "foo"
    assert a9.label == "new_foo"


def test_executions():
    ar = RefactorActions(actions=[{"action_type": "extract_untyped_parameter", "name": "foo"}])
    execution = RefactorActionExecution(action={"action_type": "extract_untyped_parameter", "name": "foo"}, messages=[])
    assert isinstance(execution.messages, (list,))
    execution = RefactorActionExecution(action=ar.actions[0].dict(), messages=[])
    assert isinstance(execution.messages, (list,))
