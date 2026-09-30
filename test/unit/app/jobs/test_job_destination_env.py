from typing import Any

import pytest

from galaxy.jobs.job_destination import JobDestination


def test_destination_scopes():
    destination = JobDestination(
        env=[
            {"name": "LEGACY", "value": "1"},
            {"type": "job", "name": "JOB", "value": "2"},
            {"type": "tool", "name": "TOOL", "value": "3"},
        ],
    )
    assert [e["name"] for e in destination.env] == ["LEGACY", "JOB", "TOOL"]
    assert destination.tool_env_names == ["TOOL"]


@pytest.mark.parametrize(
    "entry", [{"file": "/env.sh"}, {"execute": "module load x"}, {"name": "bad-name", "value": "x"}]
)
def test_tool_env_rejects_unknown_names(entry):
    # Deliberately malformed, so it can't satisfy the entry TypedDicts.
    env: list[Any] = [{"type": "tool", **entry}]
    with pytest.raises(ValueError):
        JobDestination(env=env)
