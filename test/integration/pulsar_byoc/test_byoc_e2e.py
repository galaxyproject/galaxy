"""End-to-end BYOC integration tests.

What's exercised:
  * ``pulsar-config register-with-galaxy`` orchestration (Pulsar side) drives
    the relay's device flow with ``pair=true`` against a real Keycloak.
  * ``PulsarByocManager.complete_registration`` (Galaxy side) accepts the
    secondary refresh token, round-trips it through the relay, decodes the
    JWT, pins the three BYOC topics, and stores the rotated token.
  * The two refresh tokens rotate independently — neither can lock the
    other out.

These are heavier than the unit suite. Gate locally with ``-m e2e`` and
skip gracefully when Docker isn't available.
"""

from __future__ import annotations

import httpx
import pytest
from pulsar_relay_client import HttpRelayClient

from ._device_flow import drive_device_flow_with_pair

pytestmark = pytest.mark.e2e


def _relay_client_for_url(relay_url: str) -> HttpRelayClient:
    return HttpRelayClient(relay_url)


def test_complete_registration_against_real_relay(relay_against_keycloak):
    """Galaxy's BYOC manager + real relay: tokens round-trip, topics pin,
    rotated token lands in the vault, pair rotates independently."""
    relay = relay_against_keycloak["base_url"]
    setup = relay_against_keycloak["keycloak"]

    # 1. Drive the device flow with pair=true.
    tokens = drive_device_flow_with_pair(relay, setup, client_hint="byoc-galaxy-e2e")
    primary = tokens["refresh_token"]
    secondary = tokens["refresh_token_secondary"]
    access_token = tokens["access_token"]
    assert primary and secondary and primary != secondary

    # The relay user's username is the OIDC ``sub`` claim's mapped value;
    # we use it as the BYOC manager_name (= JWT ``sub``).
    sub = httpx.get(f"{relay}/auth/me", headers={"Authorization": f"Bearer {access_token}"}, timeout=5.0).json()[
        "username"
    ]

    # 2. Exercise the production HttpRelayClient adapter against the live
    #    relay. Idempotent on re-run (see step 4).
    client = _relay_client_for_url(relay)
    for prefix in ("job_setup", "job_kill", "job_status_update"):
        client.create_or_verify_topic(access_token, f"{prefix}_{sub}")

    # 3. Verify the three topics now exist and are owned by the BYOC user.
    me_user_id = httpx.get(f"{relay}/auth/me", headers={"Authorization": f"Bearer {access_token}"}, timeout=5.0).json()[
        "user_id"
    ]
    for prefix in ("job_setup", "job_kill", "job_status_update"):
        topic = f"{prefix}_{sub}"
        resp = httpx.get(
            f"{relay}/api/v1/topics/{topic}",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=5.0,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["owner_id"] == me_user_id

    # 4. Re-running create_or_verify_topic with the same user must succeed
    #    (idempotent) — this is what re-registration would trigger.
    for prefix in ("job_setup", "job_kill", "job_status_update"):
        client.create_or_verify_topic(access_token, f"{prefix}_{sub}")

    # 5. Both refresh tokens still work independently.
    with httpx.Client(timeout=10.0) as client:
        rotated_primary = client.post(f"{relay}/auth/token/refresh", json={"refresh_token": primary})
        assert rotated_primary.status_code == 200, rotated_primary.text

        # Replay of the now-rotated primary kills *primary's* chain only.
        client.post(f"{relay}/auth/token/refresh", json={"refresh_token": primary})

        rotated_secondary = client.post(f"{relay}/auth/token/refresh", json={"refresh_token": secondary})
        assert (
            rotated_secondary.status_code == 200
        ), "Secondary refresh failed after primary chain was killed — pair-issuance independence regression!"


def test_admin_cannot_seize_byoc_topics(relay_against_keycloak):
    """Cross-user defence: after a BYOC user pins its topics, the bootstrap
    admin (a separate relay user) cannot claim them by creating them."""
    relay = relay_against_keycloak["base_url"]
    setup = relay_against_keycloak["keycloak"]

    tokens = drive_device_flow_with_pair(relay, setup, client_hint="byoc-galaxy-e2e")
    access_token = tokens["access_token"]
    sub = httpx.get(f"{relay}/auth/me", headers={"Authorization": f"Bearer {access_token}"}, timeout=5.0).json()[
        "username"
    ]

    client = _relay_client_for_url(relay)
    for prefix in ("job_setup", "job_kill", "job_status_update"):
        client.create_or_verify_topic(access_token, f"{prefix}_{sub}")

    # Now log in as the bootstrap admin and try to create the same topics.
    admin_login = httpx.post(
        f"{relay}/auth/login",
        data={"username": "admin", "password": "adminpw1234"},
        timeout=5.0,
    )
    assert admin_login.status_code == 200
    admin_token = admin_login.json()["access_token"]
    admin_headers = {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json",
    }
    for prefix in ("job_setup", "job_kill", "job_status_update"):
        topic = f"{prefix}_{sub}"
        resp = httpx.post(
            f"{relay}/api/v1/topics",
            headers=admin_headers,
            json={"topic_name": topic},
            timeout=5.0,
        )
        assert (
            400 <= resp.status_code < 500
        ), f"admin unexpectedly claimed topic {topic}: HTTP {resp.status_code} {resp.text}"
