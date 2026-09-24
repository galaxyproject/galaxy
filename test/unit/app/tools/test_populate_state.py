import json
from typing import (
    Any,
    cast,
)

import pytest

from galaxy.tools.parameters import (
    populate_state,
    ToolInputsT,
)
from galaxy.tools.parameters.basic import (
    BooleanToolParameter,
    DataToolParameter,
    SelectToolParameter,
    TextToolParameter,
)
from galaxy.tools.parameters.grouping import (
    Conditional,
    ConditionalWhen,
    Repeat,
)
from galaxy.tools.parameters.workflow_utils import workflow_building_modes
from galaxy.util import XML
from galaxy.util.bunch import Bunch

trans = Bunch(workflow_building_mode=False)
workflow_building_trans = Bunch(
    workflow_building_mode=workflow_building_modes.ENABLED, app=Bunch(name="galaxy"), history=None
)


def mock_when(**kwd):
    return cast(ConditionalWhen, Bunch(**kwd))


def test_populate_state():
    a = TextToolParameter(None, XML('<param name="a"/>'))
    b = Repeat("b")
    b.min = 0
    b.max = 1
    c = TextToolParameter(None, XML('<param name="c"/>'))
    d = Repeat("d")
    d.min = 0
    d.max = 1
    e = TextToolParameter(None, XML('<param name="e"/>'))
    f = Conditional("f")
    g = BooleanToolParameter(None, XML('<param name="g"/>'))
    h = TextToolParameter(None, XML('<param name="h"/>'))
    i = TextToolParameter(None, XML('<param name="i"/>'))
    b.inputs = {"c": c, "d": d}
    d.inputs = {"e": e, "f": f}
    f.test_param = g
    f.cases = [mock_when(value="true", inputs={"h": h}), mock_when(value="false", inputs={"i": i})]
    inputs = {"a": a, "b": b}
    flat = {"a": 1, "b_0|c": 2, "b_0|d_0|e": 3, "b_0|d_0|f|h": 4, "b_0|d_0|f|g": True}
    state: dict[str, Any] = {}
    populate_state(trans, cast(ToolInputsT, inputs), flat, state, check=False)
    assert state["a"] == 1
    assert state["b"][0]["c"] == 2
    assert state["b"][0]["d"][0]["e"] == 3
    assert state["b"][0]["d"][0]["f"]["h"] == 4
    # now test with input_format='21.01'
    nested = {"a": 1, "b": [{"c": 2, "d": [{"e": 3, "f": {"h": 4, "g": True}}]}]}
    state_new: dict[str, Any] = {}
    populate_state(trans, cast(ToolInputsT, inputs), nested, state_new, check=False, input_format="21.01")
    assert state_new["a"] == 1
    assert state_new["b"][0]["c"] == 2
    assert state_new["b"][0]["d"][0]["e"] == 3
    assert state_new["b"][0]["d"][0]["f"]["h"] == 4


def build_conditional_with_data_param():
    cond = Conditional("cond")
    cond.test_param = SelectToolParameter(
        None,
        XML("""
            <param name="select" type="select">
                <option value="a">a</option>
                <option value="b">b</option>
            </param>
            """),
    )
    inner = Conditional("inner")
    inner.test_param = SelectToolParameter(
        None, XML('<param name="inner_select" type="select"><option value="x">x</option></param>')
    )
    inner.cases = [
        mock_when(
            value="x", inputs={"input2": DataToolParameter(None, XML('<param name="input2" type="data"/>'), trans=None)}
        )
    ]
    cond.cases = [
        mock_when(
            value="a",
            inputs={
                "input1": DataToolParameter(None, XML('<param name="input1" type="data"/>'), trans=None),
                "inner": inner,
            },
        ),
        mock_when(value="b", inputs={}),
    ]
    return cond


@pytest.mark.parametrize(
    "input_format,incoming",
    [("legacy", {"cond|select": "removed_option"}), ("21.01", {"cond": {"select": "removed_option"}})],
)
def test_populate_state_serializes_runtime_values_of_unresolved_conditional(input_format, incoming):
    inputs = {"cond": build_conditional_with_data_param()}
    state: dict[str, Any] = {}
    errors: dict[str, Any] = {}
    populate_state(
        workflow_building_trans,
        cast(ToolInputsT, inputs),
        incoming,
        state,
        errors=errors,
        check=True,
        input_format=input_format,
    )
    assert errors
    assert state["cond"]["select"] == "removed_option"
    assert state["cond"]["input1"] == {"__class__": "RuntimeValue"}
    assert state["cond"]["inner"]["input2"] == {"__class__": "RuntimeValue"}
    json.dumps(state)
