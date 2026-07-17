"""Tests for the shared ``active_branch_params`` conditional-branch primitive.

``active_branch_params`` centralizes the "test parameter plus the active
branch's parameters, or just the test parameter when no branch is active"
assembly that the native strip/visit and format2 strip walkers all rely on.
"""

from galaxy.tool_util.parameters import active_branch_params
from galaxy.tool_util_models.parameters import (
    BooleanParameterModel,
    ConditionalParameterModel,
    ConditionalWhen,
    TextParameterModel,
)


def _bool(name):
    return BooleanParameterModel(name=name, type="boolean")


def _text(name):
    return TextParameterModel(name=name, type="text")


def _conditional():
    """gx_boolean conditional: the ``true`` branch adds ``threshold``, ``false`` adds nothing."""
    return ConditionalParameterModel(
        name="cond",
        type="conditional",
        test_parameter=_bool("advanced"),
        whens=[
            ConditionalWhen(discriminator=True, parameters=[_text("threshold")], is_default_when=False),
            ConditionalWhen(discriminator=False, parameters=[], is_default_when=False),
        ],
    )


def _names(params):
    return [p.name for p in params]


def test_active_branch_includes_branch_params():
    params = active_branch_params(_conditional(), {"advanced": True})
    assert _names(params) == ["advanced", "threshold"]


def test_inactive_branch_yields_only_test_parameter():
    # The ``false`` branch declares no params — only the test parameter is active.
    params = active_branch_params(_conditional(), {"advanced": False})
    assert _names(params) == ["advanced"]


def test_no_matching_branch_yields_only_test_parameter():
    # Value matches no branch and there is no default-when: no branch is active.
    conditional = ConditionalParameterModel(
        name="cond",
        type="conditional",
        test_parameter=_bool("advanced"),
        whens=[ConditionalWhen(discriminator=True, parameters=[_text("threshold")], is_default_when=False)],
    )
    params = active_branch_params(conditional, {"advanced": False})
    assert _names(params) == ["advanced"]


def test_select_hook_is_honored():
    # A selector that suppresses matching (the format2 degradation contract)
    # collapses to just the test parameter even when a branch would match.
    params = active_branch_params(_conditional(), {"advanced": True}, select=lambda *_: None)
    assert _names(params) == ["advanced"]
