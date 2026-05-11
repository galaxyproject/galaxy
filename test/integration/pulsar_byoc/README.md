# BYOC integration suite

End-to-end tests for the **Bring Your Own Compute** Pulsar feature
(`enable_pulsar_byoc: true`). They drive Galaxy's `PulsarByocManager` against
a real pulsar-relay subprocess, which is in turn backed by a real Keycloak
container.

## Prerequisites

- Docker (and either `docker compose` v2 or the legacy `docker-compose`).
- A local checkout of [`pulsar-relay`](https://github.com/galaxyproject/pulsar-relay)
  reachable via one of:
  - `PULSAR_RELAY_REPO=/path/to/pulsar-relay`
  - `/Users/mvandenb/src/pulsar-relay` (default; this developer's layout)
  - `~/src/pulsar-relay`

  The relay is run from source so the suite exercises the in-tree code —
  this lets BYOC-side changes to the relay (pair-issuance, topic ACLs,
  chain-scoped revocation) be verified before they're cut into a release.

If either prerequisite is missing the suite skips cleanly.

## Running

The suite is gated on the `e2e` marker:

```
./run_tests.sh -unit "test/integration/pulsar_byoc -m e2e"
```

Or directly:

```
pytest test/integration/pulsar_byoc -m e2e -v
```

Typical wall clock: ~90 s (Keycloak boot + relay startup + device-flow).

## What's exercised

`test_complete_registration_against_real_relay`
- RFC 8628 device flow against Keycloak with `pair=true`.
- `HttpRelayClient.create_or_verify_topic` (from `pulsar-relay-client`) for each of the three BYOC topic names, against the live relay.
- Topic ownership matches the BYOC user.
- Re-running the create-or-verify loop is idempotent.
- The primary and secondary refresh tokens rotate on independent chains —
  replaying the rotated primary kills only the primary's chain, the
  secondary keeps refreshing cleanly.

`test_admin_cannot_seize_byoc_topics`
- After a BYOC user pins its topics, the bootstrap admin can't claim them
  by re-creating them (the cross-user race defence).

## Files

- `docker-compose.yml` — Keycloak only. The relay is a subprocess.
- `conftest.py` — `keycloak` (session-scoped) and `relay_against_keycloak`
  (per-test) fixtures.
- `test_byoc_e2e.py` — the suite.

## Adding a tool-execution test

A future addition would actually submit a job: bring up a Pulsar daemon
configured against the relay (with the manager_name from the device-flow
sub claim), boot Galaxy in-process via `IntegrationTestCase`, and assert a
tool runs end-to-end through the BYOC runner. That's roughly +200 LoC and
needs the multi-tenant runner to materialise its client manager against a
live relay; deferred until the current suite has bedded in.
