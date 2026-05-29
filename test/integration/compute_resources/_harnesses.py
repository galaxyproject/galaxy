"""Subprocess lifecycle helpers for the BYOC tool-execution integration test.

The full e2e stack (Keycloak via docker-compose, pulsar-relay as a Python
subprocess, the Pulsar daemon as another Python subprocess) was previously
inlined as a stack of ``_bring_up_*`` ClassMethods on the test class.
Lifting them into module-level helpers means:

* Bring-up + teardown is callable from places other than the test class
  (e.g. ad-hoc smoke scripts).
* The test class shrinks back to what it actually does: drive BYOC bootstrap,
  submit a tool, assert.
* Each helper is independently exercisable.

These helpers do NOT use context managers because the test class needs to
hold each handle across multiple lifecycle methods (``_prepare_galaxy``,
``setUp``, ``tearDownClass``) — a single ``with`` block can't span those.
The handles are dataclasses; the test class is responsible for calling
:func:`teardown_subprocess` on each on shutdown.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import httpx
import pytest
from pulsar_relay_client import CredentialsFile

from galaxy_test.driver.keycloak import start_keycloak_http_dev

RELAY_READY_TIMEOUT_SECONDS = 30
PULSAR_READY_TIMEOUT_SECONDS = 30
LOG_TAIL_BYTES = 16_000


def _tail(path: Path, n_bytes: int = LOG_TAIL_BYTES) -> str:
    """Return the last ``n_bytes`` of a log file, or a note if it's unreadable."""
    try:
        data = path.read_bytes()
    except OSError as exc:
        return f"<could not read {path}: {exc}>"
    return data[-n_bytes:].decode(errors="replace")


@dataclass
class KeycloakHandle:
    port: int
    base_url: str
    container_name: str


@dataclass
class RelayHandle:
    port: int
    base_url: str
    process: subprocess.Popen
    log_path: Path


@dataclass
class PulsarHandle:
    process: subprocess.Popen
    pulsar_dir: Path
    credentials_path: Path
    log_path: Path


def bring_up_keycloak(*, port: int, container_name: str) -> KeycloakHandle:
    """Start Keycloak (HTTP dev mode) via the shared helper. Realm + clients
    + users are provisioned later via the admin API; see ``_keycloak_bootstrap.py``."""
    try:
        start_keycloak_http_dev(container_name=container_name, host_port=port)
    except RuntimeError as exc:
        subprocess.run(["docker", "logs", container_name], check=False)
        subprocess.run(["docker", "rm", "-f", container_name], check=False)
        pytest.fail(str(exc))
    return KeycloakHandle(port=port, base_url=f"http://localhost:{port}", container_name=container_name)


def bring_up_relay(*, port: int, base_url: str, keycloak_setup, log_path: Path) -> RelayHandle:
    """Start the pulsar-relay subprocess and wait for /health.

    The relay subprocess is given an env that points its OIDC config at
    the Keycloak provisioned for the test run. Its stdout+stderr are
    redirected to ``log_path`` rather than a ``PIPE``: an undrained pipe
    fills its OS buffer and blocks the relay mid-write (which surfaces as
    ``RemoteDisconnected`` on long-poll), and a file keeps the logs around
    for post-mortem.
    """
    env = {
        **os.environ,
        "PULSAR_JWT_SECRET_KEY": "byoc-tool-execution-jwt-secret-1234567890abcdef",
        "PULSAR_BOOTSTRAP_ADMIN_USERNAME": "admin",
        "PULSAR_BOOTSTRAP_ADMIN_PASSWORD": "adminpw1234",
        "PULSAR_BOOTSTRAP_ADMIN_EMAIL": "admin@example.com",
        "PULSAR_ALLOWED_ORIGINS": f'["{base_url}"]',
        "PULSAR_TRUSTED_HOSTS": '["localhost", "127.0.0.1"]',
        "PULSAR_OIDC__ENABLED": "true",
        "PULSAR_OIDC__BASE_URL": base_url,
        "PULSAR_OIDC__PROVIDERS__KEYCLOAK__DISPLAY_NAME": "Keycloak",
        "PULSAR_OIDC__PROVIDERS__KEYCLOAK__DISCOVERY_URL": keycloak_setup.discovery_url,
        "PULSAR_OIDC__PROVIDERS__KEYCLOAK__CLIENT_ID": keycloak_setup.client_id,
        "PULSAR_OIDC__PROVIDERS__KEYCLOAK__CLIENT_SECRET": keycloak_setup.client_secret,
        "PULSAR_OIDC__PROVIDERS__KEYCLOAK__CLAIM_USERNAME": "preferred_username",
    }
    # Open the log file and hand its fd to the child; the parent closes its
    # own copy immediately (the child keeps a dup for its lifetime).
    with open(log_path, "wb") as log_file:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "pulsar_relay.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--log-level",
                "warning",
            ],
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
        )
    deadline = time.time() + RELAY_READY_TIMEOUT_SECONDS
    while time.time() < deadline:
        try:
            with httpx.Client(timeout=1.0) as c:
                if c.get(f"{base_url}/health").status_code == 200:
                    return RelayHandle(port=port, base_url=base_url, process=process, log_path=log_path)
        except Exception:
            pass
        time.sleep(0.3)
    process.kill()
    pytest.fail(f"Relay subprocess did not start.\nRelay log ({log_path}):\n{_tail(log_path)}")


def bring_up_pulsar(
    *,
    tmp_dir: Path,
    relay_base_url: str,
    manager_name: str,
    primary_token: str,
    access_token: str,
    app_template: Path,
) -> PulsarHandle:
    """Write Pulsar's app.yml + credentials file and start the daemon.

    Waits until the pulsar daemon has published its capability snapshot to
    ``pulsar_capabilities_<manager_name>``. Unlike the job topics (which the
    caller pre-creates), this topic only comes into existence once Pulsar's
    relay consumer is actually up and polling — so it's the signal that Pulsar
    will catch a ``job_setup`` posted next. (The relay long-poll starts from the
    tail, so a job published before the consumer polls would otherwise be missed
    until the following message arrives.)
    """
    pulsar_dir = tmp_dir / "pulsar"
    staging = pulsar_dir / "staging"
    persistence = pulsar_dir / "persistence"
    for p in (pulsar_dir, staging, persistence):
        p.mkdir(parents=True, exist_ok=True)

    credentials_path = pulsar_dir / "relay_credentials.json"
    CredentialsFile(str(credentials_path)).save(
        {
            "relay_url": relay_base_url,
            "refresh_token": primary_token,
            "issued_at": "2026-05-11T00:00:00+00:00",
        }
    )

    app_yaml_path = pulsar_dir / "app.yml"
    app_yaml_path.write_text(
        app_template.read_text().format(
            manager_name=manager_name,
            message_queue_url=relay_base_url,
            credentials_file=str(credentials_path),
            staging_directory=str(staging),
            persistence_directory=str(persistence),
        )
    )
    server_ini_path = pulsar_dir / "server.ini"
    pulsar_log_path = pulsar_dir / "pulsar.log"
    server_ini_path.write_text(
        "[server:main]\nuse = egg:Paste#http\nhost = 127.0.0.1\nport = 0\n"
        "\n"
        "[loggers]\nkeys=root\n\n"
        "[handlers]\nkeys=console,file\n\n"
        "[formatters]\nkeys=default\n\n"
        "[logger_root]\nlevel=DEBUG\nhandlers=console,file\n\n"
        "[handler_console]\nclass=StreamHandler\nargs=(sys.stderr,)\n"
        "level=DEBUG\nformatter=default\n\n"
        f"[handler_file]\nclass=FileHandler\nargs=('{pulsar_log_path}', 'w')\n"
        "level=DEBUG\nformatter=default\n\n"
        "[formatter_default]\n"
        "format=%(asctime)s %(name)s %(levelname)s %(message)s\n"
    )

    env = {**os.environ}
    env["PYTHONUNBUFFERED"] = "1"
    # ``pulsar.main`` imports galaxy packages (galaxy.job_metrics, galaxy.util,
    # …). In the dev/test layout galaxy lives on ``sys.path`` via pytest's
    # ``pythonpath = lib``, which a subprocess does NOT inherit — so the daemon
    # would crash at import with ``ModuleNotFoundError: No module named
    # 'galaxy'``. Put galaxy's ``lib`` on the child's PYTHONPATH explicitly.
    import galaxy

    # ``galaxy`` is a PEP 420 namespace package (no ``__file__``); its
    # ``__path__`` entry points at ``<root>/lib/galaxy``, so its parent is the
    # ``lib`` dir we need on PYTHONPATH.
    galaxy_lib = str(Path(next(iter(galaxy.__path__))).resolve().parent)
    existing_pp = env.get("PYTHONPATH")
    env["PYTHONPATH"] = galaxy_lib if not existing_pp else os.pathsep.join([galaxy_lib, existing_pp])
    # Redirect stdout+stderr to a file (the daemon logs to stderr; the ini's
    # file handler isn't applied by ``pulsar.main``). An undrained PIPE would
    # fill its OS buffer and block the daemon mid-write — stalling job
    # consumption — so never use one for a process we don't actively drain.
    with open(pulsar_log_path, "wb") as log_file:
        process = subprocess.Popen(
            [
                sys.executable,
                "-u",
                "-m",
                "pulsar.main",
                "--config_dir",
                str(pulsar_dir),
                "--ini_path",
                str(server_ini_path),
            ],
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
        )
    # The topics are pre-created by the caller, so a 200 on the topic GET only
    # proves the topic exists — not that the daemon is alive and consuming. Guard
    # every iteration with a liveness check and re-confirm the process survived a
    # beat after the topic check, so a daemon that crashes at startup (e.g. an
    # import error) fails loudly here instead of leaving the job stuck in 'queued'.
    # ``pulsar_capabilities_<manager>`` is published by Pulsar's consumer on
    # startup and is NOT pre-created by the caller, so its existence proves the
    # consumer is live and polling.
    topic = f"pulsar_capabilities_{manager_name}"
    deadline = time.time() + PULSAR_READY_TIMEOUT_SECONDS
    headers = {"Authorization": f"Bearer {access_token}"}
    while time.time() < deadline:
        if process.poll() is not None:
            pytest.fail(
                f"Pulsar subprocess exited before subscribing.\n"
                f"Pulsar log ({pulsar_log_path}):\n{_tail(pulsar_log_path)}"
            )
        try:
            with httpx.Client(timeout=1.0) as c:
                r = c.get(f"{relay_base_url}/api/v1/topics/{topic}", headers=headers)
                if r.status_code == 200:
                    time.sleep(0.5)
                    if process.poll() is not None:
                        pytest.fail(
                            f"Pulsar subprocess exited just after startup.\n"
                            f"Pulsar log ({pulsar_log_path}):\n{_tail(pulsar_log_path)}"
                        )
                    return PulsarHandle(
                        process=process,
                        pulsar_dir=pulsar_dir,
                        credentials_path=credentials_path,
                        log_path=pulsar_log_path,
                    )
        except Exception:
            pass
        time.sleep(0.5)
    process.kill()
    pytest.fail(
        f"Pulsar did not subscribe to {topic} within {PULSAR_READY_TIMEOUT_SECONDS}s\n"
        f"Pulsar log ({pulsar_log_path}):\n{_tail(pulsar_log_path)}"
    )


def teardown_subprocess(proc: Optional[subprocess.Popen], label: str, log_path: Optional[Path] = None) -> None:
    """Terminate a subprocess (with kill escalation) and dump its log to stdout.

    Idempotent on ``None``; safe to call from teardown paths where bring-up
    may have raised before the handle was assigned. Output is read from
    ``log_path`` (the daemons redirect stdout+stderr there) rather than a PIPE,
    which we deliberately don't use — see ``bring_up_relay`` / ``bring_up_pulsar``.
    """
    if proc is None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
    if log_path is not None:
        print(f"\n--- {label} log ({log_path}) ---\n{_tail(log_path)}")
