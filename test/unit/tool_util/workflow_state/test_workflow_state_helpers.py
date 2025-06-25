from galaxy.tool_util.parameters import repeat_inputs_to_array


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
