from typing import cast

import pytest

from galaxy.managers.workflows import (
    _same_form_value,
    WorkflowContentsManager,
)
from galaxy.tools.parameters.basic import (
    BooleanToolParameter,
    DataToolParameter,
    FloatToolParameter,
    IntegerToolParameter,
    SelectToolParameter,
    TextToolParameter,
    ToolParameter,
)
from galaxy.tools.parameters.grouping import (
    Conditional,
    ConditionalWhen,
    Repeat,
    Section,
)
from galaxy.tools.parameters.workflow_utils import RuntimeValue
from galaxy.util import XML
from galaxy.util.bunch import Bunch
from galaxy.workflow.modules import ToolModule


def _param(cls, xml: str) -> ToolParameter:
    return cls(None, XML(xml))


def _int(name: str) -> ToolParameter:
    return _param(IntegerToolParameter, f'<param name="{name}" type="integer" value="1"/>')


def _module(inputs, state) -> ToolModule:
    return cast(ToolModule, Bunch(tool=Bunch(inputs=inputs), state=Bunch(inputs=state), trans=Bunch(app=None)))


def test_tool_form_defaults_selects_defaults_the_form_shows():
    conditional = Conditional("cond")
    conditional.test_param = _param(
        SelectToolParameter,
        '<param name="sel" type="select"><option value="a">A</option><option value="b">B</option></param>',
    )
    conditional.test_param.refresh_on_change = True
    case_a = ConditionalWhen()
    case_a.value = "a"
    case_a.inputs = {"x": _int("x")}
    case_b = ConditionalWhen()
    case_b.value = "b"
    case_b.inputs = {}
    conditional.cases = [case_a, case_b]
    repeat = Repeat("rep")
    repeat.inputs = {"r": _param(FloatToolParameter, '<param name="r" type="float" value="1"/>')}
    section = Section("sec")
    section.inputs = {"b": _param(BooleanToolParameter, '<param name="b" type="boolean"/>')}
    inputs = {
        "i": _int("i"),
        "d": _param(DataToolParameter, '<param name="d" type="data" format="txt"/>'),
        "connected": _int("connected"),
        "runtime": _int("runtime"),
        "invalid": _int("invalid"),
        "cond": conditional,
        "rep": repeat,
        "sec": section,
    }
    state = {
        "i": 1,
        "d": None,
        "connected": 1,
        "runtime": RuntimeValue(),
        "invalid": 1,
        "cond": {"sel": "a", "x": 1},
        "rep": [{"r": 1.0}],
        "sec": {"b": False},
    }
    defaults = {
        "i": 7,
        "d": {"class": "File", "location": "https://example.org/1.bed"},
        "connected": 7,
        "runtime": 7,
        "invalid": "not a number",
        "cond|sel": "b",
        "cond|x": "8",
        "rep_0|r": 2,
        "sec|b": "true",
        "rep_1|r": 3,
    }

    form_defaults = WorkflowContentsManager._tool_form_defaults(_module(inputs, state), defaults, {"connected"})

    assert [(name, default) for name, _, _, default in form_defaults] == [
        ("i", 7),
        ("cond|x", 8),
        ("rep_0|r", 2.0),
        ("sec|b", True),
    ]
    _, x_param, x_parent, _ = form_defaults[1]
    assert x_param is case_a.inputs["x"]
    assert x_parent is state["cond"]


@pytest.mark.parametrize(
    "param, form_value, default, same",
    [
        (_int("i"), "7", 7, True),
        (_int("i"), "3", 7, False),
        (_param(FloatToolParameter, '<param name="f" type="float" value="1"/>'), "7", 7, True),
        (_param(FloatToolParameter, '<param name="f" type="float" value="1"/>'), "7.5", 7, False),
        (_param(BooleanToolParameter, '<param name="b" type="boolean"/>'), "true", True, True),
        (_param(BooleanToolParameter, '<param name="b" type="boolean"/>'), False, True, False),
        (_param(TextToolParameter, '<param name="t" type="text"/>'), "", None, True),
        (_param(TextToolParameter, '<param name="t" type="text"/>'), "a", None, False),
        (
            _param(
                SelectToolParameter,
                '<param name="s" type="select"><option value="a">A</option><option value="b">B</option></param>',
            ),
            "a",
            "a",
            True,
        ),
    ],
)
def test_same_form_value_compares_converted_values(param, form_value, default, same):
    assert _same_form_value(param.to_python(form_value, None), param.to_python(default, None)) is same
