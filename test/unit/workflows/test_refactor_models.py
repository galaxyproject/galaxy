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
    assert isinstance(a0, AddStepAction)
    assert a0.tool_state
    assert a0.tool_state["a"] == 6
    assert a0.label == "foobar"

    a1 = actions[1]
    assert a1.action_type == "update_step_label"
    assert isinstance(a1, UpdateStepLabelAction)
    assert isinstance(a1.step, StepReferenceByOrderIndex)
    assert a1.step.order_index == 5

    a2 = actions[2]
    assert isinstance(a2, UpdateStepLabelAction)
    assert isinstance(a2.step, StepReferenceByLabel)
    assert a2.step.label == "cool_label"

    a3 = actions[3]
    assert a3.action_type == "connect"
    assert isinstance(a3, ConnectAction)
    # Verify it sets default output_name
    assert a3.output.output_name == "output"
    assert a3.input.input_name == "foobar"

    a4 = actions[4]
    assert isinstance(a4, DisconnectAction)
    assert a4.output.output_name == "o_name"
    assert isinstance(a4.input, InputReferenceByLabel)
    assert a4.input.input_name == "foobar2"
    assert a4.input.label == "foolabel"

    a5 = actions[5]
    assert isinstance(
        a5,
        AddInputAction,
    )
    assert a5.type == "data"
    assert a5.optional is False

    a6 = actions[6]
    assert isinstance(
        a6,
        AddInputAction,
    )
    assert a6.optional is True
    assert a6.default == 5

    a7 = actions[7]
    assert isinstance(
        a7,
        ExtractInputAction,
    )
    assert isinstance(a7.input, InputReferenceByOrderIndex)
    assert a7.input.order_index == 5
    assert a7.input.input_name == "foobar"

    a8 = actions[8]
    assert isinstance(
        a8,
        ExtractUntypedParameter,
    )
    assert a8.name == "foo"
    assert a8.label is None

    a9 = actions[9]
    assert isinstance(
        a9,
        ExtractUntypedParameter,
    )
    assert a9.name == "foo"
    assert a9.label == "new_foo"


def test_executions():
    ar = RefactorActions(actions=[{"action_type": "extract_untyped_parameter", "name": "foo"}])
    execution = RefactorActionExecution(action={"action_type": "extract_untyped_parameter", "name": "foo"}, messages=[])
    assert isinstance(execution.messages, (list,))
    execution = RefactorActionExecution(action=ar.actions[0].model_dump(), messages=[])
    assert isinstance(execution.messages, (list,))
