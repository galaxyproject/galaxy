from galaxy.tool_util.parameters import repeat_inputs_to_array
from galaxy.tool_util.workflow_state._util import (
    step_inline_tool_class,
    step_is_inline_tool,
    step_tool_representation,
)


def test_repeat_inputs_to_array():
    rval = repeat_inputs_to_array(
        "repeatfoo",
        {
            "moo": "cow",
        },
    )
    assert not rval
    test_state: dict = {
        "moo": "cow",
        "repeatfoo_0|moocow": ["moo"],
        "repeatfoo_2|moocow": ["cow"],
    }
    rval = repeat_inputs_to_array("repeatfoo", test_state)
    assert len(rval) == 3
    assert "repeatfoo_0|moocow" in rval[0]
    assert "repeatfoo_0|moocow" not in rval[1]
    assert "repeatfoo_0|moocow" not in rval[2]
    assert "repeatfoo_2|moocow" not in rval[1]
    assert "repeatfoo_2|moocow" in rval[2]


USER_TOOL_REPR = {
    "class": "GalaxyUserTool",
    "id": "cat_user_defined",
    "name": "cat_user_defined",
    "version": "0.1",
    "container": "busybox",
    "shell_command": "cat '$(inputs.input1.path)' > output.txt",
    "inputs": [{"name": "input1", "type": "data", "format": "txt"}],
    "outputs": [{"name": "output1", "type": "data", "format": "txt", "from_work_dir": "output.txt"}],
}


def test_step_tool_representation_none_for_regular_step():
    step = {"id": 0, "type": "tool", "tool_id": "cat1", "tool_version": "1.0.0"}
    assert step_tool_representation(step) is None
    assert step_inline_tool_class(step) is None
    assert step_is_inline_tool(step) is False


def test_step_tool_representation_user_tool():
    step = {"id": 0, "type": "tool", "tool_representation": USER_TOOL_REPR}
    assert step_tool_representation(step) == USER_TOOL_REPR
    assert step_inline_tool_class(step) == "GalaxyUserTool"
    assert step_is_inline_tool(step) is True


def test_step_inline_tool_class_admin_dynamic_tool():
    step = {
        "id": 0,
        "type": "tool",
        "tool_representation": {"class": "GalaxyTool", "name": "admin tool"},
    }
    assert step_inline_tool_class(step) == "GalaxyTool"
    assert step_is_inline_tool(step) is True


def test_step_inline_tool_class_unknown_class_ignored():
    step = {
        "id": 0,
        "type": "tool",
        "tool_representation": {"class": "SomethingElse"},
    }
    assert step_inline_tool_class(step) is None
    assert step_is_inline_tool(step) is False
