"""Unit tests for the multi-tenant PulsarMQBYOCJobRunner.

These tests exercise the BYOC-specific lookup/cache/recovery logic in
isolation. The Pulsar client factory is injected via the runner's
``client_manager_factory`` kwarg so tests never touch the network or
``MagicMock.assert_called_*`` — they inspect the fake's recorded calls
directly (state verification, not interaction verification).
"""

from typing import Any
from unittest.mock import MagicMock

import pytest

from galaxy.jobs.runners.pulsar import (
    BYOCClientManagerRegistry,
    PulsarMQBYOCJobRunner,
)


class _StubResource:
    def __init__(
        self,
        *,
        id: int,
        manager_name: str,
        relay_url: str = "https://relay.test",
        relay_topic_prefix: str | None = None,
        status: str = "active",
    ):
        self.id = id
        self.manager_name = manager_name
        self.relay_url = relay_url
        self.relay_topic_prefix = relay_topic_prefix
        self.status = status


class _StubUser:
    def __init__(self, id: int):
        self.id = id


class _StubVault:
    """Minimal Vault double; tracks reads and writes per key."""

    def __init__(self, initial=None):
        self._store: dict[str, str] = dict(initial or {})
        self.reads: list[str] = []
        self.writes: list[tuple[str, str]] = []

    def read_secret(self, key: str):
        self.reads.append(key)
        return self._store.get(key)

    def write_secret(self, key: str, value: str) -> None:
        self.writes.append((key, value))
        self._store[key] = value

    def list_secrets(self, key: str):
        return [k for k in self._store if k.startswith(key)]


class _StubSession:
    def __init__(self, resources_by_id):
        self._resources = resources_by_id
        self._jobs: dict[int, object] = {}

    def get(self, model_cls, pk):
        # Caller passes the SQLAlchemy class; we dispatch by name.
        if model_cls.__name__ == "PulsarByocResource":
            return self._resources.get(pk)
        if model_cls.__name__ == "Job":
            return self._jobs.get(pk)
        return None


class _StubByocManager:
    """Stand-in for ``app.byoc_manager`` exposing only the surface the
    runner uses (``capabilities_for``). Tests set ``snapshot`` to control
    what the runner sees; ``calls`` records each invocation."""

    def __init__(self, snapshot=None):
        self.snapshot = snapshot
        self.calls: list = []

    def capabilities_for(self, resource, *, user):
        self.calls.append((resource, user))
        return self.snapshot


class _StubApp:
    def __init__(self, resources_by_id, vault, byoc_manager=None):
        self.model = MagicMock()
        self.model.session = _StubSession(resources_by_id)
        self.vault = vault
        self.byoc_manager = byoc_manager or _StubByocManager(snapshot=None)


class _StubJobDestination:
    def __init__(self, params: dict[str, Any]) -> None:
        self.params = params


class _RecordingJobWrapper:
    """Records ``fail()`` calls in plain attributes so tests can assert on
    *state* (the wrapper was failed, with this message) rather than on
    MagicMock's call_args introspection."""

    def __init__(self, destination_params: dict[str, Any]) -> None:
        self.job_destination = _StubJobDestination(destination_params)
        self.failures: list[str] = []

    def fail(self, message: str) -> None:
        self.failures.append(message)


class _StubJob:
    def __init__(self, id: int, user: "_StubUser") -> None:
        self.id = id
        self.user = user


class _FakeClientManager:
    """A recording fake for pulsar.client.manager.ClientManagerInterface.

    The runner only calls three methods on the returned object after
    construction: ``ensure_has_status_update_callback``, ``ensure_has_ack_consumers``,
    and ``shutdown``. Recording each lets tests verify *state* (the manager
    was shut down) rather than asserting on mock interactions.
    """

    def __init__(self) -> None:
        self.shutdowns = 0
        self.status_callbacks: list = []
        self.ack_consumers_armed = 0

    def ensure_has_status_update_callback(self, callback) -> None:
        self.status_callbacks.append(callback)

    def ensure_has_ack_consumers(self) -> None:
        self.ack_consumers_armed += 1

    def shutdown(self) -> None:
        self.shutdowns += 1


class _FakeClientManagerFactory:
    """Records every ``build_client_manager`` call the runner makes and
    returns a fresh ``_FakeClientManager`` per call."""

    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.created: list[_FakeClientManager] = []

    def __call__(self, **kwargs) -> _FakeClientManager:
        self.calls.append(kwargs)
        cm = _FakeClientManager()
        self.created.append(cm)
        return cm


def _make_runner(*, resources_by_id, vault, runner_params=None, factory=None, byoc_manager=None):
    """Build a PulsarMQBYOCJobRunner bypassing its inherited __init__.

    ``factory`` is the ``client_manager_factory`` that __init__ would
    normally store — we just attach it directly because we're skipping
    the chain. ``byoc_manager`` is the stub the downgrade tests use to
    drive ``self.app.byoc_manager.capabilities_for``.
    """
    runner = object.__new__(PulsarMQBYOCJobRunner)
    # We bypass __init__ to skip worker-thread setup; mypy sees these
    # attributes as the parent class's exact types but the runtime methods
    # we exercise only use the simple in-test surface.
    runner.app = _StubApp(resources_by_id, vault, byoc_manager=byoc_manager)  # type: ignore[assignment]
    runner.runner_params = runner_params or {  # type: ignore[assignment]
        "manager": None,
        "cache": None,
        "transport": None,
        "persistence_directory": None,
    }
    runner.client_manager_kwargs = {}
    runner._registry = BYOCClientManagerRegistry(factory or _FakeClientManagerFactory())
    return runner


@pytest.fixture
def vault_with_token():
    user = _StubUser(id=7)
    vault = _StubVault({f"user/{user.id}/pulsar_byoc/42/relay_refresh_token": "RT-AAA"})
    return user, vault


def test_lazy_creates_one_client_manager_per_resource(vault_with_token):
    user, vault = vault_with_token
    resource = _StubResource(id=42, manager_name="byoc_7_lab")
    factory = _FakeClientManagerFactory()
    runner = _make_runner(resources_by_id={42: resource}, vault=vault, factory=factory)

    params = {"pulsar_byoc_resource_id": 42}
    cm1 = runner._get_or_create_client_manager(params, user)
    cm2 = runner._get_or_create_client_manager(params, user)

    assert cm1 is cm2
    assert len(factory.calls) == 1
    kwargs = factory.calls[0]
    assert kwargs["relay_url"] == "https://relay.test"
    assert kwargs["manager"] == "byoc_7_lab"
    assert kwargs["relay_refresh_token"] == "RT-AAA"
    # The on_save callback must be wired so rotated tokens get persisted.
    assert callable(kwargs["on_refresh_token_rotated"])
    # The status-update callback must be wired immediately, not deferred.
    assert len(cm1.status_callbacks) == 1
    assert cm1.ack_consumers_armed == 1


def test_different_resources_get_different_client_managers():
    user_a, user_b = _StubUser(id=1), _StubUser(id=2)
    vault = _StubVault(
        {
            f"user/{user_a.id}/pulsar_byoc/10/relay_refresh_token": "RT-A",
            f"user/{user_b.id}/pulsar_byoc/20/relay_refresh_token": "RT-B",
        }
    )
    resources = {
        10: _StubResource(id=10, manager_name="byoc_1_one"),
        20: _StubResource(id=20, manager_name="byoc_2_two"),
    }
    factory = _FakeClientManagerFactory()
    runner = _make_runner(resources_by_id=resources, vault=vault, factory=factory)

    cm_a = runner._get_or_create_client_manager({"pulsar_byoc_resource_id": 10}, user_a)
    cm_b = runner._get_or_create_client_manager({"pulsar_byoc_resource_id": 20}, user_b)

    assert cm_a is not cm_b
    assert len(factory.calls) == 2
    # Each call carried the right manager_name for its tenant.
    managers = sorted(c["manager"] for c in factory.calls)
    assert managers == ["byoc_1_one", "byoc_2_two"]


def test_non_active_resource_is_refused(vault_with_token):
    user, vault = vault_with_token
    resource = _StubResource(id=42, manager_name="byoc_7_lab", status="disabled")
    runner = _make_runner(resources_by_id={42: resource}, vault=vault)

    with pytest.raises(RuntimeError, match="not 'active'"):
        runner._get_or_create_client_manager({"pulsar_byoc_resource_id": 42}, user)


def test_missing_resource_is_refused():
    user = _StubUser(id=7)
    vault = _StubVault()
    runner = _make_runner(resources_by_id={}, vault=vault)

    with pytest.raises(RuntimeError, match="No PulsarByocResource"):
        runner._get_or_create_client_manager({"pulsar_byoc_resource_id": 999}, user)


def test_missing_vault_token_is_refused():
    user = _StubUser(id=7)
    vault = _StubVault()  # No secrets at all
    resource = _StubResource(id=42, manager_name="byoc_7_lab")
    factory = _FakeClientManagerFactory()
    runner = _make_runner(resources_by_id={42: resource}, vault=vault, factory=factory)

    with pytest.raises(RuntimeError, match="No relay refresh token"):
        runner._get_or_create_client_manager({"pulsar_byoc_resource_id": 42}, user)
    # Vault was consulted at the right key
    assert vault.reads == [f"user/{user.id}/pulsar_byoc/42/relay_refresh_token"]
    # The factory MUST NOT have been called when the token is missing.
    assert factory.calls == []


def test_rotation_callback_persists_to_vault(vault_with_token):
    """When the in-memory store rotates the refresh token, the on_save
    callback we pass to Pulsar must write the new value back into Galaxy's
    vault — otherwise the next process picks up a stale token and gets
    locked out."""
    user, vault = vault_with_token
    resource = _StubResource(id=42, manager_name="byoc_7_lab")
    factory = _FakeClientManagerFactory()
    runner = _make_runner(resources_by_id={42: resource}, vault=vault, factory=factory)

    runner._get_or_create_client_manager({"pulsar_byoc_resource_id": 42}, user)
    rotated_callback = factory.calls[0]["on_refresh_token_rotated"]

    rotated_callback(
        {
            "relay_url": "https://relay.test",
            "refresh_token": "RT-ROTATED",
            "issued_at": "2026-05-11T00:00:00+00:00",
        }
    )

    assert (f"user/{user.id}/pulsar_byoc/42/relay_refresh_token", "RT-ROTATED") in vault.writes


def test_shutdown_closes_all_cached_client_managers(monkeypatch):
    """Each materialised client manager must be told to shut down so its
    long-poll thread can stop and the relay-transport session can close."""
    # Skip AsynchronousJobRunner.shutdown (it touches worker queues that
    # aren't initialised on our bypass-__init__ instance).
    monkeypatch.setattr(
        "galaxy.jobs.runners.pulsar.AsynchronousJobRunner.shutdown",
        lambda self: None,
    )

    user = _StubUser(id=7)
    vault = _StubVault(
        {
            f"user/{user.id}/pulsar_byoc/10/relay_refresh_token": "RT-A",
            f"user/{user.id}/pulsar_byoc/20/relay_refresh_token": "RT-B",
        }
    )
    resources = {
        10: _StubResource(id=10, manager_name="byoc_7_one"),
        20: _StubResource(id=20, manager_name="byoc_7_two"),
    }
    factory = _FakeClientManagerFactory()
    runner = _make_runner(resources_by_id=resources, vault=vault, factory=factory)

    cm1 = runner._get_or_create_client_manager({"pulsar_byoc_resource_id": 10}, user)
    cm2 = runner._get_or_create_client_manager({"pulsar_byoc_resource_id": 20}, user)

    runner.shutdown()

    assert cm1.shutdowns == 1
    assert cm2.shutdowns == 1
    assert len(runner._registry) == 0


def test_recover_fails_job_cleanly_when_resource_deleted():
    """If the BYOC resource has been purged while a job was running, the
    next recovery attempt must fail the job — not crash the recovery loop."""
    user = _StubUser(id=7)
    runner = _make_runner(resources_by_id={}, vault=_StubVault())

    job = _StubJob(id=99, user=user)
    job_wrapper = _RecordingJobWrapper({"pulsar_byoc_resource_id": 42})

    runner.recover(job, job_wrapper)

    assert len(job_wrapper.failures) == 1
    assert "BYOC resource removed" in job_wrapper.failures[0]


# ---- _apply_capability_downgrades ---------------------------------------


def _make_snapshot(
    *,
    manager_name: str = "byoc_7_lab",
    staging_directory: str = "/srv/pulsar/files/staging",
    docker: bool = False,
    singularity: bool = False,
    apptainer: bool = False,
    conda: bool = False,
) -> dict:
    return {
        "schema_version": 1,
        "manager_name": manager_name,
        "pulsar_version": "0.15.16",
        "staging_directory": staging_directory,
        "persistence_directory": "/srv/pulsar/files/persisted",
        "tool_dependency_dir": None,
        "dependency_resolvers": [],
        "conda_available": conda,
        "container_runtime": {
            "docker_available": docker,
            "singularity_available": singularity,
            "apptainer_available": apptainer,
        },
        "manager": {"name": manager_name, "type": "queued_python", "num_concurrent_jobs": 1},
    }


def _runner_with_snapshot(snapshot, *, vault=None):
    user = _StubUser(id=7)
    if vault is None:
        vault = _StubVault({f"user/{user.id}/pulsar_byoc/42/relay_refresh_token": "RT-AAA"})
    resource = _StubResource(id=42, manager_name="byoc_7_lab")
    byoc_manager = _StubByocManager(snapshot=snapshot)
    runner = _make_runner(
        resources_by_id={42: resource},
        vault=vault,
        byoc_manager=byoc_manager,
    )
    return runner, user, byoc_manager


def test_downgrade_no_op_when_no_resource_id():
    runner, user, _ = _runner_with_snapshot(_make_snapshot())
    params = {"docker_enabled": True}  # no pulsar_byoc_resource_id
    runner._apply_capability_downgrades(params, user)
    assert params == {"docker_enabled": True}


def test_downgrade_no_op_when_capabilities_for_returns_none():
    """No snapshot → trust operator params verbatim."""
    runner, user, byoc_manager = _runner_with_snapshot(snapshot=None)
    params = {
        "pulsar_byoc_resource_id": 42,
        "docker_enabled": True,
        "dependency_resolution": "remote",
    }
    runner._apply_capability_downgrades(params, user)
    assert params["docker_enabled"] is True
    assert params["dependency_resolution"] == "remote"
    assert byoc_manager.calls == [(byoc_manager.calls[0][0], user)]


# --- jobs_directory auto-fill ---


def test_downgrade_fills_jobs_directory_when_unset():
    runner, user, _ = _runner_with_snapshot(_make_snapshot(staging_directory="/srv/staging"))
    params: dict[str, Any] = {"pulsar_byoc_resource_id": 42}
    runner._apply_capability_downgrades(params, user)
    assert params["jobs_directory"] == "/srv/staging"


def test_downgrade_fills_jobs_directory_when_set_to_required_sentinel():
    """The destination_default sentinel means "operator must supply this";
    the snapshot's staging_directory is exactly that operator-supplied
    value, so use it."""
    from galaxy.jobs.runners.pulsar import PARAMETER_SPECIFICATION_REQUIRED

    runner, user, _ = _runner_with_snapshot(_make_snapshot(staging_directory="/srv/staging"))
    params = {"pulsar_byoc_resource_id": 42, "jobs_directory": PARAMETER_SPECIFICATION_REQUIRED}
    runner._apply_capability_downgrades(params, user)
    assert params["jobs_directory"] == "/srv/staging"


def test_downgrade_leaves_matching_jobs_directory_alone():
    runner, user, _ = _runner_with_snapshot(_make_snapshot(staging_directory="/srv/staging"))
    params = {"pulsar_byoc_resource_id": 42, "jobs_directory": "/srv/staging"}
    runner._apply_capability_downgrades(params, user)
    assert params["jobs_directory"] == "/srv/staging"


def test_downgrade_warns_on_mismatched_jobs_directory_but_does_not_overwrite(caplog):
    """Operator override wins (perhaps they know something we don't)
    but they get a loud warning that paths will be wrong."""
    runner, user, _ = _runner_with_snapshot(_make_snapshot(staging_directory="/srv/staging"))
    params = {"pulsar_byoc_resource_id": 42, "jobs_directory": "/some/other/path"}
    runner._apply_capability_downgrades(params, user)
    assert params["jobs_directory"] == "/some/other/path"  # unchanged
    assert any("path rewrites WILL be wrong" in r.message for r in caplog.records)


def test_downgrade_no_op_when_snapshot_has_no_staging_directory():
    snap = _make_snapshot()
    snap["staging_directory"] = None
    runner, user, _ = _runner_with_snapshot(snap)
    params = {"pulsar_byoc_resource_id": 42}
    runner._apply_capability_downgrades(params, user)
    assert "jobs_directory" not in params


# --- container runtimes (clear-only) ---


@pytest.mark.parametrize(
    "param_name,available_kw",
    [
        ("docker_enabled", "docker"),
        ("singularity_enabled", "singularity"),
        ("apptainer_enabled", "apptainer"),
    ],
)
def test_downgrade_clears_runtime_flag_when_remote_lacks_it(param_name, available_kw, caplog):
    snapshot_kwargs: dict[str, Any] = {available_kw: False}
    runner, user, _ = _runner_with_snapshot(_make_snapshot(**snapshot_kwargs))
    params: dict[str, Any] = {"pulsar_byoc_resource_id": 42, param_name: True}
    runner._apply_capability_downgrades(params, user)
    assert params[param_name] is False
    assert any(f"requested {param_name}=true" in r.message for r in caplog.records)


@pytest.mark.parametrize(
    "param_name,available_kw",
    [
        ("docker_enabled", "docker"),
        ("singularity_enabled", "singularity"),
        ("apptainer_enabled", "apptainer"),
    ],
)
def test_downgrade_preserves_runtime_flag_when_remote_has_it(param_name, available_kw):
    snapshot_kwargs: dict[str, Any] = {available_kw: True}
    runner, user, _ = _runner_with_snapshot(_make_snapshot(**snapshot_kwargs))
    params: dict[str, Any] = {"pulsar_byoc_resource_id": 42, param_name: True}
    runner._apply_capability_downgrades(params, user)
    assert params[param_name] is True


def test_downgrade_does_not_set_runtime_flag_when_operator_did_not_request_it():
    """Clear-only: even if pulsar reports docker available, we never auto-enable it."""
    runner, user, _ = _runner_with_snapshot(_make_snapshot(docker=True))
    params = {"pulsar_byoc_resource_id": 42}
    runner._apply_capability_downgrades(params, user)
    assert "docker_enabled" not in params


def test_downgrade_clears_remote_container_handling_when_no_runtime_at_all(caplog):
    runner, user, _ = _runner_with_snapshot(_make_snapshot())  # all runtimes False
    params = {"pulsar_byoc_resource_id": 42, "remote_container_handling": True}
    runner._apply_capability_downgrades(params, user)
    assert params["remote_container_handling"] is False
    assert any("no container runtime" in r.message for r in caplog.records)


def test_downgrade_keeps_remote_container_handling_if_any_runtime_present():
    """Even one runtime is enough to honor the request."""
    runner, user, _ = _runner_with_snapshot(_make_snapshot(singularity=True))
    params = {"pulsar_byoc_resource_id": 42, "remote_container_handling": True}
    runner._apply_capability_downgrades(params, user)
    assert params["remote_container_handling"] is True


# --- conda dependency resolution ---


def test_downgrade_demotes_dependency_resolution_remote_to_none_when_no_conda(caplog):
    runner, user, _ = _runner_with_snapshot(_make_snapshot(conda=False))
    params = {"pulsar_byoc_resource_id": 42, "dependency_resolution": "remote"}
    runner._apply_capability_downgrades(params, user)
    # NOT "local" — that would be a broken path on a non-shared FS.
    assert params["dependency_resolution"] == "none"
    assert any("downgrading to 'none'" in r.message for r in caplog.records)


def test_downgrade_keeps_dependency_resolution_remote_when_conda_available():
    runner, user, _ = _runner_with_snapshot(_make_snapshot(conda=True))
    params = {"pulsar_byoc_resource_id": 42, "dependency_resolution": "remote"}
    runner._apply_capability_downgrades(params, user)
    assert params["dependency_resolution"] == "remote"


@pytest.mark.parametrize("resolution", ["local", "none"])
def test_downgrade_does_not_touch_non_remote_dependency_resolution(resolution):
    """Operator already opted out of remote conda; we don't second-guess."""
    runner, user, _ = _runner_with_snapshot(_make_snapshot(conda=False))
    params = {"pulsar_byoc_resource_id": 42, "dependency_resolution": resolution}
    runner._apply_capability_downgrades(params, user)
    assert params["dependency_resolution"] == resolution
