"""The destination keeps one ordered, serializable list outside persisted params."""

import json

import pytest

from galaxy.jobs.environment import normalize_environment_entry
from galaxy.jobs.job_destination import JobDestination
from galaxy.jobs.runners.util.env import env_to_statement


def test_scoped_entries_keep_order_and_legacy_constructor():
    destination = JobDestination(
        env=[
            {"name": "LEGACY", "value": "1"},
            {"type": "tool", "name": "X", "value": "tool"},
            {"type": "job", "name": "X", "value": "job"},
        ]
    )
    assert [entry["type"] for entry in destination.env] == ["job", "tool", "job"]
    assert destination.tool_env_names == ["X"]
    assert [env_to_statement(entry) for entry in destination.env] == [
        'LEGACY="1"; export LEGACY',
        'X="tool"; export X',
        'X="job"; export X',
    ]
    assert json.loads(json.dumps(destination.env)) == destination.env
    assert destination.params == {}


def test_legacy_mutation_and_reordering():
    destination = JobDestination(env=[{"type": "tool", "name": "X", "value": "tool"}])
    destination.env.append({"name": "X", "value": "later"})
    destination.env.insert(0, {"name": "X", "value": "earlier"})
    assert [entry["value"] for entry in destination.env] == ["earlier", "tool", "later"]
    assert destination.tool_env_names == ["X"]
    destination.env.reverse()
    assert [entry["value"] for entry in destination.env] == ["later", "tool", "earlier"]


@pytest.mark.parametrize(
    "entry",
    [
        {"type": "invalid"},
        {"type": "tool", "file": "/env.sh"},
        {"type": "tool", "execute": "module load x"},
        {"type": "tool", "name": "X"},
        {"type": "tool", "name": "bad-name", "value": "x"},
        {"type": "tool", "name": "X", "value": None},
    ],
)
def test_invalid_scoped_entries_are_rejected(entry):
    with pytest.raises(ValueError):
        normalize_environment_entry(entry)


def test_explicit_config_scope_wins():
    assert normalize_environment_entry({"type": "tool", "name": "X", "value": "x"}, "job")["type"] == "job"
    assert normalize_environment_entry({"name": "EMPTY", "value": ""}, "tool") == {
        "type": "tool",
        "name": "EMPTY",
        "value": "",
    }
