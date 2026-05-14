"""Unit tests for :class:`RelayCapabilitiesCache` and :func:`extract_capability_payload`.

The cache is a small TTL dict keyed by ``(relay_url, manager_name)``;
the helper validates a ``PaginatedMessagesResponse`` body and returns the
payload (or ``None`` for unusable shapes). Both are pure / mockable, so
these tests don't need a Galaxy app fixture.
"""
from __future__ import annotations

from typing import (
    Any,
    Optional,
)

import pytest

from galaxy.managers.pulsar_byoc import (
    CAPABILITIES_CACHE_TTL_SECONDS,
    RelayCapabilitiesCache,
    SUPPORTED_CAPABILITIES_SCHEMA_VERSIONS,
    _make_capabilities_topic_name,
    extract_capability_payload,
)


# --- _make_capabilities_topic_name ----------------------------------------


@pytest.mark.parametrize(
    "prefix,manager_name,expected",
    [
        (None, "_default_", "pulsar_capabilities"),
        ("", "_default_", "pulsar_capabilities"),
        (None, "cluster_a", "pulsar_capabilities_cluster_a"),
        ("prod", "_default_", "prod_pulsar_capabilities"),
        ("prod", "cluster_a", "prod_pulsar_capabilities_cluster_a"),
    ],
)
def test_topic_name_matches_publisher_convention(prefix: Optional[str], manager_name: str, expected: str) -> None:
    """Mirrors pulsar/messaging/bind_relay.py:__make_capabilities_topic_name.

    Drift here desynchronizes Galaxy's reads from Pulsar's publishes;
    keep these explicit.
    """
    assert _make_capabilities_topic_name(prefix, manager_name) == expected


# --- extract_capability_payload -------------------------------------------


def _response(*messages: dict[str, Any]) -> dict[str, Any]:
    return {
        "messages": list(messages),
        "total": len(messages),
        "limit": 1,
        "order": "desc",
        "cursor": None,
        "next_cursor": None,
    }


def _msg(payload: Any) -> dict[str, Any]:
    return {
        "message_id": "1700000000-0",
        "topic": "pulsar_capabilities",
        "payload": payload,
        "timestamp": "2026-05-14T10:00:00.000Z",
        "metadata": None,
    }


def test_extract_returns_payload_for_supported_schema():
    payload = {"schema_version": 1, "manager_name": "_default_", "staging_directory": "/srv/staging"}
    out = extract_capability_payload(_response(_msg(payload)), "pulsar_capabilities", "https://relay")
    assert out == payload


def test_extract_returns_none_when_messages_empty():
    out = extract_capability_payload(_response(), "pulsar_capabilities", "https://relay")
    assert out is None


def test_extract_returns_none_when_payload_not_dict(caplog):
    out = extract_capability_payload(_response(_msg("not a dict")), "pulsar_capabilities", "https://relay")
    assert out is None
    assert any("non-dict payload" in r.message for r in caplog.records)


def test_extract_returns_none_for_unknown_schema_version(caplog):
    payload = {"schema_version": 99, "manager_name": "x"}
    out = extract_capability_payload(_response(_msg(payload)), "pulsar_capabilities", "https://relay")
    assert out is None
    assert any("schema_version=99" in r.message for r in caplog.records)


def test_extract_returns_none_when_schema_version_missing(caplog):
    payload = {"manager_name": "x"}  # no schema_version field at all
    out = extract_capability_payload(_response(_msg(payload)), "pulsar_capabilities", "https://relay")
    assert out is None
    assert any("schema_version=None" in r.message for r in caplog.records)


def test_supported_schema_versions_constant_unchanged():
    """If we ever add a new schema version we MUST coordinate with the
    publisher — guard against silently accepting a new version that
    Galaxy can't actually parse."""
    assert SUPPORTED_CAPABILITIES_SCHEMA_VERSIONS == frozenset({1})


# --- RelayCapabilitiesCache -----------------------------------------------


def test_cache_default_ttl():
    """The default TTL (60s) matches the design doc — a regression here
    would either spam relay traffic (too short) or hide config changes
    after pulsar restarts (too long)."""
    cache = RelayCapabilitiesCache()
    assert cache._ttl == CAPABILITIES_CACHE_TTL_SECONDS == 60.0


def test_cache_miss_invokes_fetch_once():
    cache = RelayCapabilitiesCache(ttl_seconds=60)
    calls = []

    def fetch():
        calls.append(1)
        return {"schema_version": 1}

    out = cache.get("https://r", "m", fetch)
    assert out == {"schema_version": 1}
    assert calls == [1]


def test_cache_hit_returns_value_without_re_fetching():
    cache = RelayCapabilitiesCache(ttl_seconds=60)
    calls = []

    def fetch():
        calls.append(1)
        return {"schema_version": 1, "v": "first"}

    cache.get("https://r", "m", fetch)
    # Subsequent gets within TTL must skip fetch entirely.
    out2 = cache.get("https://r", "m", fetch)
    assert out2 == {"schema_version": 1, "v": "first"}
    assert calls == [1]


def test_cache_caches_none_results():
    """A pulsar that hasn't published or that errored once shouldn't
    trigger an HTTP fetch on every job within the TTL window."""
    cache = RelayCapabilitiesCache(ttl_seconds=60)
    calls = []

    def fetch():
        calls.append(1)
        return None

    assert cache.get("https://r", "m", fetch) is None
    assert cache.get("https://r", "m", fetch) is None
    assert calls == [1]  # second call hit cache, didn't re-fetch


def test_cache_expires_after_ttl():
    # Inject a manual clock so the test is deterministic and instant.
    fake_time = [0.0]
    cache = RelayCapabilitiesCache(ttl_seconds=0.05, clock=lambda: fake_time[0])
    calls = []

    def fetch():
        calls.append(1)
        return {"schema_version": 1, "v": len(calls)}

    cache.get("https://r", "m", fetch)
    # Advance past the TTL.
    fake_time[0] = 0.10
    out = cache.get("https://r", "m", fetch)
    assert out is not None
    assert out["v"] == 2
    assert len(calls) == 2


def test_cache_invalidate_forces_refresh():
    cache = RelayCapabilitiesCache(ttl_seconds=60)
    calls = []

    def fetch():
        calls.append(1)
        return {"schema_version": 1, "v": len(calls)}

    cache.get("https://r", "m", fetch)
    cache.invalidate("https://r", "m")
    cache.get("https://r", "m", fetch)
    assert len(calls) == 2


def test_cache_keys_are_per_relay_and_manager():
    """Two pulsars under the same relay or two relays for the same
    manager must not share a cache slot."""
    cache = RelayCapabilitiesCache(ttl_seconds=60)
    cache.get("https://r1", "m", lambda: {"v": "r1m"})
    cache.get("https://r2", "m", lambda: {"v": "r2m"})
    cache.get("https://r1", "n", lambda: {"v": "r1n"})

    # Subsequent calls hit the right slot (the lambdas would otherwise
    # be invoked again).
    assert cache.get("https://r1", "m", lambda: pytest.fail("r1/m re-fetched")) == {"v": "r1m"}
    assert cache.get("https://r2", "m", lambda: pytest.fail("r2/m re-fetched")) == {"v": "r2m"}
    assert cache.get("https://r1", "n", lambda: pytest.fail("r1/n re-fetched")) == {"v": "r1n"}


def test_cache_swallows_fetch_errors_via_caller_contract():
    """The cache itself doesn't catch — fetch closures handle their own
    errors and return ``None``. Verifies the contract by asserting an
    exception in fetch propagates."""
    cache = RelayCapabilitiesCache(ttl_seconds=60)

    def boom():
        raise RuntimeError("network broke")

    with pytest.raises(RuntimeError, match="network broke"):
        cache.get("https://r", "m", boom)
