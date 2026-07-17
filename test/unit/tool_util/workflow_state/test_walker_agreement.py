"""Cross-walker parity: ``strip_undeclared_keys`` vs ``classify_stale_keys``.

Both walk native tool_state against a tool definition and decide which keys are
undeclared, but from opposite ends — one deletes, the other categorizes. This
pins the invariant that they agree on *which* keys are stale: the set the
cleaner removes (while preserving bookkeeping keys) must equal the set the
classifier reports as non-bookkeeping stale.

Guards the drift risk called out in the walker convergence work: the two
traversals share ``select_which_when_native`` / ``active_branch_params`` but keep
independent recursion, so a change to one that silently desyncs the other should
turn this red.
"""

import copy

import pytest

from galaxy.tool_util.parameters import (
    NATIVE_BOOKKEEPING_KEYS,
    strip_undeclared_keys,
)
from galaxy.tool_util.workflow_state.stale_keys import (
    classify_stale_keys,
    StaleKeyCategory,
)
from galaxy.tool_util_models.parameters import (
    BooleanParameterModel,
    ConditionalParameterModel,
    ConditionalWhen,
    IntegerParameterModel,
    RepeatParameterModel,
    SectionParameterModel,
    SelectParameterModel,
)


class _Inputs:
    """Minimal ToolInputs stand-in — classify only needs ``.inputs``."""

    def __init__(self, inputs):
        self.inputs = inputs


def _int(name):
    return IntegerParameterModel(name=name, type="integer")


def _bool(name):
    return BooleanParameterModel(name=name, type="boolean")


def _select(name):
    return SelectParameterModel(name=name, type="select")


def _cond(name, test, whens):
    return ConditionalParameterModel(name=name, type="conditional", test_parameter=test, whens=whens)


def _when(discriminator, parameters):
    return ConditionalWhen(discriminator=discriminator, parameters=parameters, is_default_when=False)


def _repeat(name, parameters):
    return RepeatParameterModel(name=name, type="repeat", parameters=parameters)


def _section(name, parameters):
    return SectionParameterModel(name=name, type="section", parameters=parameters)


def _norm(path: str) -> str:
    """Strip uses ``|`` between levels, classify uses ``.`` — normalize to compare."""
    return path.replace("|", ".")


def _classify_nonbookkeeping(state, inputs):
    keys = classify_stale_keys({"tool_state": state}, _Inputs(inputs))
    return {_norm(k.key_path) for k in keys if k.category is not StaleKeyCategory.BOOKKEEPING}


def _strip_removed(state, inputs):
    removed: list[str] = []
    # Preserve bookkeeping so the removed set is comparable to classify's
    # non-bookkeeping set (classify never reports bookkeeping keys as stale).
    strip_undeclared_keys(copy.deepcopy(state), inputs, removed, preserve_keys=NATIVE_BOOKKEEPING_KEYS)
    return {_norm(p) for p in removed}


# (id, tool_inputs, state) — cases where the two walkers must agree.
PARITY_CASES = [
    (
        "flat_unknown",
        [_int("a")],
        {"a": 1, "junk": 2},
    ),
    (
        "bookkeeping_top_level",
        [_int("a")],
        {"a": 1, "__page__": 0, "__rerun_remap_job_id__": None},
    ),
    (
        "conditional_active_branch_stale",
        [_cond("cond", _bool("adv"), [_when(True, [_int("thr")])])],
        {"cond": {"adv": True, "thr": 1, "junk": 2}},
    ),
    (
        "conditional_inactive_branch_leak",
        [_cond("cond", _select("mode"), [_when("a", [_int("pa")]), _when("b", [_int("pb")])])],
        {"cond": {"mode": "a", "pa": 1, "pb": 9}},
    ),
    (
        "repeat_instance_stale",
        [_repeat("r", [_int("item")])],
        {"r": [{"item": 1, "extra": 2}, {"item": 3}]},
    ),
    (
        "section_stale",
        [_section("s", [_int("item")])],
        {"s": {"item": 1, "extra": 2}},
    ),
    (
        "section_nested_bookkeeping",
        [_section("s", [_int("item")])],
        {"s": {"item": 1, "__page__": 0}},
    ),
    (
        "stale_root_conditional_leak",
        [_cond("cond", _select("mode"), [_when("a", [_int("pa")])])],
        {"mode": "a", "cond": {"mode": "a", "pa": 1}},
    ),
]


@pytest.mark.parametrize("case_id, inputs, state", PARITY_CASES, ids=[c[0] for c in PARITY_CASES])
def test_strip_classify_parity(case_id, inputs, state):
    assert _strip_removed(state, inputs) == _classify_nonbookkeeping(state, inputs)


@pytest.mark.xfail(
    strict=True,
    reason="classify skips an inactive conditional with no default-when; strip still prunes its orphaned params",
)
def test_inactive_conditional_without_default_known_gap():
    inputs = [_cond("cond", _select("mode"), [_when("a", [_int("pa")]), _when("b", [_int("pb")])])]
    # test value "c" matches no branch and there is no default-when.
    state = {"cond": {"mode": "c", "pa": 1}}
    assert _strip_removed(state, inputs) == _classify_nonbookkeeping(state, inputs)
