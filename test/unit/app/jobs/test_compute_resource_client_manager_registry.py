"""Direct unit tests for :class:`ComputeResourceClientManagerRegistry`.

The registry is the per-tenant client-manager cache lifted out of
``PulsarMQBYOCJobRunner`` so its lazy-create / cache-hit / shutdown
contract can be exercised without bypassing the runner's __init__ or
patching ``AsynchronousJobRunner.shutdown``.
"""

from __future__ import annotations

from typing import Any

from galaxy.jobs.runners.pulsar import ComputeResourceClientManagerRegistry


class _FakeClientManager:
    """Records the calls the runner makes on returned client managers so
    tests verify *state*, not interaction-mock plumbing."""

    def __init__(self) -> None:
        self.shutdowns = 0
        self.status_callbacks: list = []
        self.ack_consumers_armed = 0

    def ensure_has_status_update_callback(self, callback: Any) -> None:
        self.status_callbacks.append(callback)

    def ensure_has_ack_consumers(self) -> None:
        self.ack_consumers_armed += 1

    def shutdown(self) -> None:
        self.shutdowns += 1


def _factory_recorder() -> tuple[list[dict[str, Any]], list[_FakeClientManager], Any]:
    """Returns ``(calls, created, factory)`` for ergonomic test assertions."""
    calls: list[dict[str, Any]] = []
    created: list[_FakeClientManager] = []

    def factory(**kwargs: Any) -> _FakeClientManager:
        calls.append(kwargs)
        cm = _FakeClientManager()
        created.append(cm)
        return cm

    return calls, created, factory


def test_returns_cached_client_manager_on_repeat_lookup():
    calls, _created, factory = _factory_recorder()
    registry = ComputeResourceClientManagerRegistry(factory)
    key = ("https://relay.test", "manager_a")

    cm1 = registry.get_or_create(key, kwargs_builder=lambda: {"relay_url": key[0], "manager": key[1]})
    cm2 = registry.get_or_create(key, kwargs_builder=lambda: {"relay_url": key[0], "manager": key[1]})

    assert cm1 is cm2
    assert len(calls) == 1


def test_different_keys_get_distinct_client_managers():
    _calls, _created, factory = _factory_recorder()
    registry = ComputeResourceClientManagerRegistry(factory)

    cm_a = registry.get_or_create(
        ("https://relay.test", "manager_a"),
        kwargs_builder=lambda: {"relay_url": "https://relay.test", "manager": "manager_a"},
    )
    cm_b = registry.get_or_create(
        ("https://relay.test", "manager_b"),
        kwargs_builder=lambda: {"relay_url": "https://relay.test", "manager": "manager_b"},
    )
    assert cm_a is not cm_b
    assert len(registry) == 2


def test_kwargs_builder_skipped_on_cache_hit():
    """The kwargs builder is what does the expensive vault read; the cache
    hit must not pay that cost on every job."""
    _calls, _created, factory = _factory_recorder()
    registry = ComputeResourceClientManagerRegistry(factory)
    key = ("https://relay.test", "manager_a")
    build_count = [0]

    def kwargs_builder() -> dict[str, Any]:
        build_count[0] += 1
        return {"relay_url": key[0], "manager": key[1]}

    registry.get_or_create(key, kwargs_builder=kwargs_builder)
    registry.get_or_create(key, kwargs_builder=kwargs_builder)
    assert build_count[0] == 1


def test_on_create_invoked_once_per_fresh_manager():
    calls, _created, factory = _factory_recorder()
    registry = ComputeResourceClientManagerRegistry(factory)
    key = ("https://relay.test", "manager_a")
    on_create_invocations: list[_FakeClientManager] = []

    def kwargs_builder() -> dict[str, Any]:
        return {"relay_url": key[0], "manager": key[1]}

    def on_create(cm: _FakeClientManager) -> None:
        on_create_invocations.append(cm)

    cm1 = registry.get_or_create(key, kwargs_builder=kwargs_builder, on_create=on_create)
    cm2 = registry.get_or_create(key, kwargs_builder=kwargs_builder, on_create=on_create)
    assert cm1 is cm2
    assert on_create_invocations == [cm1]
    assert len(calls) == 1


def test_shutdown_drains_all_cached_managers():
    _calls, created, factory = _factory_recorder()
    registry = ComputeResourceClientManagerRegistry(factory)

    registry.get_or_create(("https://relay.test", "m_a"), kwargs_builder=lambda: {"a": 1})
    registry.get_or_create(("https://relay.test", "m_b"), kwargs_builder=lambda: {"b": 2})
    assert len(registry) == 2

    registry.shutdown()
    assert all(cm.shutdowns == 1 for cm in created)
    assert len(registry) == 0


def test_shutdown_swallows_per_manager_exceptions():
    """One client manager throwing in shutdown must not prevent the others
    from being drained or the registry from being emptied."""

    class _ExplodingClientManager(_FakeClientManager):
        def shutdown(self) -> None:
            raise RuntimeError("boom")

    created: list[Any] = []

    def factory(**kwargs: Any) -> Any:
        cm: Any = _ExplodingClientManager() if kwargs.get("explode") else _FakeClientManager()
        created.append(cm)
        return cm

    registry = ComputeResourceClientManagerRegistry(factory)
    registry.get_or_create(("https://relay.test", "m_ok"), kwargs_builder=lambda: {"explode": False})
    registry.get_or_create(("https://relay.test", "m_boom"), kwargs_builder=lambda: {"explode": True})
    registry.get_or_create(("https://relay.test", "m_ok2"), kwargs_builder=lambda: {"explode": False})

    registry.shutdown()
    # Both ok managers were shut down; the boom raise was swallowed; the
    # cache is empty even though one shutdown raised.
    ok_managers = [
        c for c in created if isinstance(c, _FakeClientManager) and not isinstance(c, _ExplodingClientManager)
    ]
    assert all(c.shutdowns == 1 for c in ok_managers)
    assert len(registry) == 0
