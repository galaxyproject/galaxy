"""Unit tests for the Kubernetes job runner pod security context."""

from types import SimpleNamespace
from typing import (
    Any,
    cast,
)

import pytest

from galaxy.jobs.runners import RunnerParams
from galaxy.jobs.runners.kubernetes import (
    KubernetesJobRunner,
    RUNNER_PARAM_SPECS,
    valid_fs_group_change_policy,
)


def _runner(runner_params=None):
    runner = cast(Any, object.__new__(KubernetesJobRunner))
    runner.app = SimpleNamespace(config=SimpleNamespace(gid=10001))
    runner.runner_params = RunnerParams(specs=RUNNER_PARAM_SPECS, params=runner_params or {})
    return runner


def _job_wrapper(destination_params=None):
    return SimpleNamespace(job_destination=SimpleNamespace(params=destination_params or {}))


def _security_context(runner, job_wrapper):
    return runner._KubernetesJobRunner__get_k8s_security_context(job_wrapper)


def test_security_context_from_runner_params():
    runner = _runner(dict(k8s_run_as_user_id="10001", k8s_run_as_group_id="10001", k8s_fs_group_id="10001"))
    assert _security_context(runner, _job_wrapper()) == {
        "runAsUser": 10001,
        "runAsGroup": 10001,
        "fsGroup": 10001,
    }


def test_fs_group_change_policy_from_runner_params():
    runner = _runner(dict(k8s_fs_group_id="10001", k8s_fs_group_change_policy="OnRootMismatch"))
    security_context = _security_context(runner, _job_wrapper())
    assert security_context["fsGroup"] == 10001
    assert security_context["fsGroupChangePolicy"] == "OnRootMismatch"


def test_fs_group_change_policy_from_destination_params():
    runner = _runner(dict(k8s_fs_group_id="10001"))
    job_wrapper = _job_wrapper(dict(k8s_fs_group_change_policy="OnRootMismatch"))
    assert _security_context(runner, job_wrapper)["fsGroupChangePolicy"] == "OnRootMismatch"


def test_destination_fs_group_change_policy_overrides_runner_params():
    runner = _runner(dict(k8s_fs_group_id="10001", k8s_fs_group_change_policy="Always"))
    job_wrapper = _job_wrapper(dict(k8s_fs_group_change_policy="OnRootMismatch"))
    assert _security_context(runner, job_wrapper)["fsGroupChangePolicy"] == "OnRootMismatch"


@pytest.mark.parametrize("policy", [None, ""])
def test_fs_group_change_policy_unset(policy):
    runner = _runner(dict(k8s_fs_group_id="10001"))
    job_wrapper = _job_wrapper(dict(k8s_fs_group_change_policy=policy))
    assert "fsGroupChangePolicy" not in _security_context(runner, job_wrapper)
    assert "fsGroupChangePolicy" not in _security_context(runner, _job_wrapper())


def test_fs_group_change_policy_runner_param_validation():
    assert valid_fs_group_change_policy("OnRootMismatch")
    assert valid_fs_group_change_policy("Always")
    assert valid_fs_group_change_policy(None)
    assert valid_fs_group_change_policy("")
    assert not valid_fs_group_change_policy("onrootmismatch")
    assert not valid_fs_group_change_policy("Never")


def test_fs_group_change_policy_rejected_by_runner_params():
    with pytest.raises(Exception, match="k8s_fs_group_change_policy"):
        RunnerParams(specs=RUNNER_PARAM_SPECS, params=dict(k8s_fs_group_change_policy="Never"))
