"""Shared RFC 8628 device-flow driver for BYOC integration tests.

Both :mod:`test_byoc_e2e` and :mod:`test_byoc_tool_execution` need to drive
the relay's device-flow + Keycloak operator login + token exchange — exactly
the same RFC 8628 polling loop with ``pair=true``. Lifted here so the two
suites cannot drift on ``slow_down`` handling, polling interval back-off,
or operator-thread exception propagation.
"""

from __future__ import annotations

import time
from concurrent.futures import (
    ThreadPoolExecutor,
    TimeoutError as FutureTimeoutError,
)
from typing import Any

import httpx
import pytest

from ._keycloak_login import login_via_keycloak

_DEVICE_GRANT = "urn:ietf:params:oauth:grant-type:device_code"

_DEFAULT_POLL_DEADLINE_SECONDS = 60
_DEFAULT_OPERATOR_TIMEOUT_SECONDS = 60


def drive_device_flow_with_pair(
    relay: str,
    keycloak_setup: Any,
    *,
    client_hint: str = "byoc-integration",
    poll_deadline_seconds: int = _DEFAULT_POLL_DEADLINE_SECONDS,
    operator_timeout_seconds: int = _DEFAULT_OPERATOR_TIMEOUT_SECONDS,
) -> dict:
    """Drive device-flow + Keycloak sign-in + token exchange against a live relay.

    Returns the ``/auth/device/token`` JSON body — which carries
    ``access_token`` / ``refresh_token`` / ``refresh_token_secondary``.

    The operator-side Keycloak sign-in runs on a worker thread; its
    exception (if any) is propagated via :class:`ThreadPoolExecutor` so
    tests see the real failure, not a stale ``device-flow polling never
    completed`` timeout.
    """
    with httpx.Client(timeout=10.0) as client:
        dev = client.post(
            f"{relay}/auth/device/code",
            data={"client_hint": client_hint, "pair": "true"},
        )
        assert dev.status_code == 200, dev.text
        body = dev.json()
        device_code = body["device_code"]
        user_code = body["user_code"]
        interval = max(int(body["interval"]), 1)

    def operator() -> None:
        with httpx.Client(timeout=10.0, follow_redirects=False) as op:
            start = op.get(
                f"{relay}/auth/oidc/keycloak/login",
                params={"device_user_code": user_code},
            )
            assert start.status_code == 302
            final = login_via_keycloak(
                authorization_url=start.headers["location"],
                username=keycloak_setup.user_username,
                password=keycloak_setup.user_password,
                follow_relay_callback=True,
            )
            assert final.status_code == 200

    with ThreadPoolExecutor(max_workers=1) as pool:
        op_future = pool.submit(operator)
        try:
            deadline = time.time() + poll_deadline_seconds
            with httpx.Client(timeout=10.0) as client:
                while time.time() < deadline:
                    time.sleep(interval)
                    poll = client.post(
                        f"{relay}/auth/device/token",
                        data={"grant_type": _DEVICE_GRANT, "device_code": device_code},
                    )
                    if poll.status_code == 200:
                        return poll.json()
                    err = poll.json().get("error", "")
                    if err in ("authorization_pending", "slow_down"):
                        if err == "slow_down":
                            interval += 5
                        continue
                    pytest.fail(f"Unexpected device-flow error: {poll.status_code} {poll.text}")
            pytest.fail("device-flow polling never completed")
        finally:
            # Surface any operator-side failure rather than masking it
            # behind the polling timeout above.
            try:
                op_future.result(timeout=operator_timeout_seconds)
            except FutureTimeoutError:
                pass
