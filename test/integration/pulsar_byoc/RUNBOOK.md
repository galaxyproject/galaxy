# BYOC e2e runbook (for Claude in a Docker-enabled environment)

Paste this back to Claude in any session that has Docker reachable, and it
will run + validate the full BYOC integration harness. The harness lives
in `test/integration/pulsar_byoc/` of this Galaxy worktree.

## TL;DR commands

```bash
# From the repo root:
source /Users/mvandenb/src/galaxy/.venv/bin/activate

# Sanity-check Docker
docker info > /dev/null && docker compose version

# Configure where the relay + pulsar checkouts live (defaults shown).
export PULSAR_RELAY_REPO=${PULSAR_RELAY_REPO:-$HOME/src/pulsar-relay}
export PULSAR_REPO=${PULSAR_REPO:-$HOME/src/pulsar}

# One-time env prep (see "Environment setup" below for the why).
pip install -e "$PULSAR_RELAY_REPO"
export PYTHONPATH="$PWD/lib:$PULSAR_REPO"

# 1. Light e2e: pair-issuance + topic-ACL pinning. No Pulsar.
.venv/bin/python -m pytest \
    test/integration/pulsar_byoc/test_byoc_e2e.py \
    -m e2e -v --no-cov 2>&1 | tee /tmp/byoc_light_e2e.log

# 2. Heavy e2e: full tool-execution stack. Adds Pulsar subprocess + Galaxy.
.venv/bin/python -m pytest \
    test/integration/pulsar_byoc/test_byoc_tool_execution.py \
    -m e2e -v --no-cov 2>&1 | tee /tmp/byoc_tool_exec.log
```

## Environment setup (one-time, before the TL;DR)

The harness imports the relay package from `$PULSAR_RELAY_REPO` and shells
out to `python -m pulsar.main` against `$PULSAR_REPO`. The Galaxy `.venv`
doesn't carry either of them by default. Fixes verified in the last run:

1. **Install pulsar-relay editable into Galaxy's `.venv`** — its runtime
   deps (e.g. `prometheus_fastapi_instrumentator`) aren't otherwise
   present. From the Galaxy repo root with the venv active:
   ```bash
   pip install -e "$PULSAR_RELAY_REPO"
   ```
2. **Put both Galaxy `lib/` and `$PULSAR_REPO` on `PYTHONPATH`** so
   subprocesses started by the test pick up the BYOC-patched local
   pulsar tree rather than any older copy installed into the venv:
   ```bash
   export PYTHONPATH="$PWD/lib:$PULSAR_REPO"
   ```
   Without this, the `pulsar.main --mode webless` subprocess resolves to
   the installed `pulsar-app` and silently uses the older `_per_handler_cursor_path`
   signature, breaking cross-tenant cursor isolation.

## Prerequisites checklist

Before running, verify each line. If any fails, stop and fix it; the
tests skip silently on missing deps and you'll think they passed.

- [ ] `docker info` exits 0 (daemon is up).
- [ ] `docker compose version` exits 0. If it doesn't, `docker-compose
      --version` is acceptable too (the harness picks whichever works).
- [ ] `$PULSAR_RELAY_REPO/pulsar_relay/main.py` exists and is the
      pair-issuance-enabled tree — verify by grepping for `pair`:
      `grep -q 'pair: bool = Form(False)' $PULSAR_RELAY_REPO/pulsar_relay/api/device.py`.
- [ ] `$PULSAR_REPO/pulsar/main.py` exists and the BYOC client extensions
      are present — verify with:
      `grep -q 'InMemoryCredentialsStore' $PULSAR_REPO/pulsar/client/relay_credentials.py`.
- [ ] The Galaxy `.venv` is set up. From the Galaxy repo root:
      `[ -d .venv ] || (uv venv .venv && source .venv/bin/activate && uv pip install -r lib/galaxy/dependencies/dev-requirements.txt -r requirements.txt)`.
- [ ] Port `KEYCLOAK_HOST_PORT` (8089 by default) is free, or let the
      fixture allocate one automatically (it does).
- [ ] Quay.io is reachable (`docker pull quay.io/keycloak/keycloak:26.0`).

## What each test covers

### `test_byoc_e2e.py` (~30 s once Keycloak is up)

| Test | Asserts |
|------|---------|
| `test_complete_registration_against_real_relay` | Device-flow with `pair=true` → two refresh tokens; `HttpRelayClient.create_or_verify_topic` creates the three BYOC topics; primary rotates and replay revokes only its own chain; secondary keeps refreshing. |
| `test_admin_cannot_seize_byoc_topics` | After the BYOC user pins its topics, the bootstrap admin can't create the same topic names — defends against pre-creation race. |

### `test_byoc_tool_execution.py` (~50 s)

| Test | Asserts |
|------|---------|
| `test_framework_tool_runs_via_byoc` | A framework tool (`environment_variables`) submitted through Galaxy is routed by TPV to `pulsar_byoc`, dispatched to a real Pulsar subprocess via the relay, and the result comes back as `state=ok`. Job's `destination_params` carry the resource id + manager name TPV injected. |

## Expected output (happy path)

```
test/integration/pulsar_byoc/test_byoc_e2e.py::test_complete_registration_against_real_relay PASSED
test/integration/pulsar_byoc/test_byoc_e2e.py::test_admin_cannot_seize_byoc_topics PASSED
test/integration/pulsar_byoc/test_byoc_tool_execution.py::TestPulsarByocToolExecution::test_framework_tool_runs_via_byoc PASSED

================== 3 passed in ~85 s ==================
```

A `SKIPPED` result here is a **failure of the runbook** — the harness
believed Docker or the repo paths were unavailable. Re-check the
prerequisites.

## Troubleshooting

### "Docker daemon not reachable; skipping"
- Confirm `docker info` works. macOS Docker Desktop sometimes hangs after
  sleep — `killall com.docker.helper` and restart Desktop.
- The harness's docker check has a 5-second timeout; if your daemon is
  slow to respond, increase via your shell's Docker config (no harness
  knob).

### "pulsar-relay source tree not found"
- Verify `$PULSAR_RELAY_REPO` points at a tree containing
  `pulsar_relay/main.py`. The default fallback is `~/src/pulsar-relay`.

### "Keycloak did not become ready within 3 minutes"
- Run `docker compose -f test/integration/pulsar_byoc/docker-compose.yml logs keycloak`.
- The most common cause is the image pull failing. Pre-pull manually:
  `docker pull quay.io/keycloak/keycloak:26.0`.
- The fixture brings down the compose on failure so a second run starts
  fresh.

### "Relay subprocess did not start"
- The fixture prints captured `stdout` and `stderr` from the relay process
  on failure. Look for missing env vars or import errors — most often a
  stale `$PULSAR_RELAY_REPO` pointing at a tree without the pair-issuance
  changes.

### "Pulsar did not subscribe to job_setup_<sub> within 30s"
- Indicates Pulsar started but never registered its consumer with the
  relay. The captured stderr usually shows a `RelayAuthError` or a
  credentials-file path mismatch.
- Verify `$PULSAR_REPO/pulsar/client/manager.py` includes the
  `manager_name`-aware cursor path (`grep -q 'manager_name=self.manager_name'`).
- Subscription is HTTP long-poll, not pub/sub: the relay's topic only
  appears after the harness pre-creates it via `POST /api/v1/topics`.
  The fixture does this; if you've hand-rolled a variation, make sure
  you pre-create the three `job_*_<sub>` topics before starting Pulsar.
- For runtime diagnosis, set `BYOC_E2E_TMP=/tmp/byoc-debug` and inspect
  `/tmp/byoc-debug/pulsar/pulsar.log` after the failure — the Pulsar
  app.yml routes a DEBUG-level FileHandler there.

### Tool-execution test passes but `job.destination_params` is empty
- TPV rule didn't fire. Either the YAML rendering went wrong (look in
  `$BYOC_E2E_TMP/tpv_config.yml`) or `app.byoc_manager` isn't wired up
  (regression of step 2 in the original plan).
- Set `BYOC_E2E_TMP=/tmp/byoc-debug` before the test run to keep the
  rendered configs after the test exits.

### Test passes once but flakes on re-run
- Compose resources sometimes linger. Force-down between runs:
  `docker compose -f test/integration/pulsar_byoc/docker-compose.yml down -v`.
- Pulsar's `persistence_directory` from a prior run can confuse the new
  relay user's identity. The fixture uses a fresh `$BYOC_E2E_TMP` per
  class run by default; if you've overridden it, delete the directory
  manually.

## What's NOT in the harness (and could be added later)

- **`pulsar-config register-with-galaxy` CLI** exercising the full
  bootstrap end-to-end (currently the test inserts the BYOC resource
  directly via SQLAlchemy and skips the API surface). The unit tests at
  `test/galaxy_byoc_test.py` in `~/src/pulsar` cover the CLI surface
  against mocked HTTP, so the missing integration here is "real Galaxy
  receives a real `POST /bootstrap`."
- **Kill -9 mid-job + restart**: tearing down `_pulsar_proc` mid-test and
  asserting recovery via the lazy client-manager path.
- **Resource-deleted-mid-job**: pre-existing in unit suite as
  `test_recover_fails_job_cleanly_when_resource_deleted`; live verification
  would require this harness.

## Cleanup after a failed run

```bash
# Compose
docker compose -f test/integration/pulsar_byoc/docker-compose.yml down -v

# Lingering relay / pulsar Python processes (rare; the fixtures usually clean up)
pkill -f 'uvicorn pulsar_relay.main:app'
pkill -f 'pulsar.main'

# Per-test tmpdirs (if you set BYOC_E2E_TMP)
rm -rf "${BYOC_E2E_TMP:-/tmp/byoc_e2e_*}"
```

## Reporting back

If any test fails, attach:

1. The full pytest output (you've got it in `/tmp/byoc_*.log`).
2. The captured relay + Pulsar stderr (printed by the heavy test's
   `tearDownClass`).
3. The contents of `$BYOC_E2E_TMP` if you set it.
4. `docker compose -f test/integration/pulsar_byoc/docker-compose.yml logs keycloak`.

If everything passes, just report:

> BYOC e2e: 3 passed, 0 failed, 0 skipped. Wall time: `<n>` minutes.
