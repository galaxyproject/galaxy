import pytest

from galaxy.tools.parameters import (
    params_from_strings,
    params_to_strings,
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
from galaxy.workflow.modules import (
    same_form_value,
    step_input_form_defaults,
)


def _param(cls, xml: str) -> ToolParameter:
    return cls(None, XML(xml))


def _int(name: str) -> ToolParameter:
    return _param(IntegerToolParameter, f'<param name="{name}" type="integer" value="1"/>')


def test_step_input_form_defaults_selects_defaults_the_form_shows():
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

    form_defaults = step_input_form_defaults(inputs, state, defaults, {"connected"}, None)

    assert [(form_default.name, form_default.value) for form_default in form_defaults] == [
        ("i", 7),
        ("cond|x", 8),
        ("rep_0|r", 2.0),
        ("sec|b", True),
    ]
    assert form_defaults[1].param is case_a.inputs["x"]
    assert form_defaults[1].parent is state["cond"]


def test_step_input_form_defaults_match_the_saved_form_state():
    inputs = {
        "t": _param(TextToolParameter, '<param name="t" type="text" value=""/>'),
        "s": _param(
            SelectToolParameter,
            '<param name="s" type="select"><option value="1">1</option><option value="2">2</option></param>',
        ),
    }
    state = {"t": "", "s": "2"}
    defaults = {"t": 7, "s": 1}
    for form_default in step_input_form_defaults(inputs, state, defaults, (), None):
        form_default.parent[form_default.param.name] = form_default.value
    saved_state = params_from_strings(inputs, params_to_strings(inputs, state, None), None)

    form_defaults = step_input_form_defaults(inputs, saved_state, defaults, (), None)

    assert [form_default.name for form_default in form_defaults] == ["t", "s"]
    for form_default in form_defaults:
        assert same_form_value(form_default.parent[form_default.param.name], form_default.value)


@pytest.mark.parametrize(
    "form_value, default, same",
    [
        ("", None, True),
        (None, "", True),
        ("a", None, False),
        (None, 0, False),
        (7, 7, True),
        (3, 7, False),
    ],
)
def test_same_form_value_treats_empty_values_as_equal(form_value, default, same):
    assert same_form_value(form_value, default) is same
