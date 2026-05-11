"""Unit tests for the multi-tenant PulsarMQBYOCJobRunner.

These tests exercise the BYOC-specific lookup/cache/recovery logic in
isolation. The Pulsar client factory is injected via the runner's
``client_manager_factory`` kwarg so tests never touch the network or
``MagicMock.assert_called_*`` — they inspect the fake's recorded calls
directly (state verification, not interaction verification).
"""

import threading
from unittest.mock import MagicMock

import pytest

from galaxy.jobs.runners.pulsar import PulsarMQBYOCJobRunner


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


class _StubApp:
    def __init__(self, resources_by_id, vault):
        self.model = MagicMock()
        self.model.session = _StubSession(resources_by_id)
        self.vault = vault


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


def _make_runner(*, resources_by_id, vault, runner_params=None, factory=None):
    """Build a PulsarMQBYOCJobRunner bypassing its inherited __init__.

    ``factory`` is the ``client_manager_factory`` that __init__ would
    normally store — we just attach it directly because we're skipping
    the chain.
    """
    runner = object.__new__(PulsarMQBYOCJobRunner)
    # We bypass __init__ to skip worker-thread setup; mypy sees these
    # attributes as the parent class's exact types but the runtime methods
    # we exercise only use the simple in-test surface.
    runner.app = _StubApp(resources_by_id, vault)  # type: ignore[assignment]
    runner.runner_params = runner_params or {  # type: ignore[assignment]
        "manager": None,
        "cache": None,
        "transport": None,
        "persistence_directory": None,
    }
    runner.client_manager_kwargs = {}
    runner._client_managers = {}
    runner._client_managers_lock = threading.RLock()
    runner._client_manager_factory = factory or _FakeClientManagerFactory()
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
    assert runner._client_managers == {}


def test_recover_fails_job_cleanly_when_resource_deleted():
    """If the BYOC resource has been purged while a job was running, the
    next recovery attempt must fail the job — not crash the recovery loop."""
    user = _StubUser(id=7)
    runner = _make_runner(resources_by_id={}, vault=_StubVault())

    job = MagicMock(id=99, user=user)
    job_wrapper = MagicMock()
    job_wrapper.job_destination.params = {"pulsar_byoc_resource_id": 42}

    runner.recover(job, job_wrapper)

    job_wrapper.fail.assert_called_once()
    failure_message = job_wrapper.fail.call_args.args[0]
    assert "BYOC resource removed" in failure_message
