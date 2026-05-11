"""Fixtures for Galaxy's BYOC integration suite.

Brings up an OIDC IdP (Keycloak) via docker-compose, then a pulsar-relay
subprocess wired up to it. The Galaxy side runs in-process so the suite
can exercise ``PulsarByocManager`` against the real relay HTTP API
without the cost of a full Galaxy server boot.

Skips automatically when ``docker`` is not on ``$PATH``, the daemon
isn't reachable, or the ``pulsar_relay`` server package isn't installed.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest

from ._keycloak_bootstrap import (
    KeycloakSetup,
    provision,
)

# pulsar-relay (the *server* package, distinct from pulsar-relay-client)
# is the FastAPI app the suite launches under uvicorn. Skip rather than
# error when it isn't installed — the e2e suite is heavy and devs often
# run the unit tests without a full integration env.
if importlib.util.find_spec("pulsar_relay") is None:
    pytest.skip(
        "pulsar-relay (server) is not installed; pip install pulsar-relay to run BYOC e2e",
        allow_module_level=True,
    )

HARNESS_DIR = Path(__file__).parent
COMPOSE_FILE = HARNESS_DIR / "docker-compose.yml"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return int(s.getsockname()[1])


def _compose_cmd() -> list[str]:
    docker = shutil.which("docker")
    if docker is not None:
        try:
            subprocess.run([docker, "compose", "version"], check=True, capture_output=True, timeout=5)
            return [docker, "compose"]
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            pass
    legacy = shutil.which("docker-compose")
    if legacy is not None:
        return [legacy]
    pytest.skip("docker / docker-compose not available")
    raise RuntimeError("unreachable")


def _docker_running() -> bool:
    docker = shutil.which("docker")
    if docker is None:
        return False
    try:
        subprocess.run([docker, "info"], check=True, capture_output=True, timeout=5)
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False


@pytest.fixture(scope="session")
def keycloak() -> Iterator[Any]:
    """Boot Keycloak via docker compose; provision the test realm; tear down."""
    if not _docker_running():
        pytest.skip("Docker daemon not reachable; skipping BYOC integration suite.")

    compose = _compose_cmd()
    host_port = int(os.environ.get("KEYCLOAK_HOST_PORT") or _free_port())
    env = {**os.environ, "KEYCLOAK_HOST_PORT": str(host_port)}

    subprocess.run(
        [*compose, "-f", str(COMPOSE_FILE), "up", "-d", "keycloak"],
        check=True,
        env=env,
    )
    base_url = f"http://localhost:{host_port}"

    deadline = time.time() + 180
    while time.time() < deadline:
        try:
            with httpx.Client(timeout=2.0) as c:
                r = c.get(f"{base_url}/realms/master")
                if r.status_code in (200, 302):
                    break
        except Exception:
            pass
        time.sleep(2)
    else:
        subprocess.run([*compose, "-f", str(COMPOSE_FILE), "logs", "keycloak"], env=env)
        subprocess.run([*compose, "-f", str(COMPOSE_FILE), "down", "-v"], env=env)
        pytest.fail("Keycloak did not become ready within 3 minutes")

    yield KeycloakSetup(base_url=base_url)

    subprocess.run([*compose, "-f", str(COMPOSE_FILE), "down", "-v"], env=env)


@pytest.fixture
def relay_against_keycloak(keycloak, tmp_path: Path) -> Iterator[dict]:
    """Boot a pulsar-relay subprocess against the running Keycloak.

    Mirrors pulsar-relay's own ``relay_against_keycloak`` fixture; copied
    (not imported) because pytest fixture sharing across packages is fragile.
    """
    relay_port = _free_port()
    base_url = f"http://localhost:{relay_port}"
    callback = f"{base_url}/auth/oidc/keycloak/callback"

    setup = provision(redirect_uris=[callback], setup=KeycloakSetup(base_url=keycloak.base_url))

    env = {
        **os.environ,
        "PULSAR_JWT_SECRET_KEY": "byoc-integration-test-jwt-secret-1234567890abcdef",
        "PULSAR_BOOTSTRAP_ADMIN_USERNAME": "admin",
        "PULSAR_BOOTSTRAP_ADMIN_PASSWORD": "adminpw1234",
        "PULSAR_BOOTSTRAP_ADMIN_EMAIL": "admin@example.com",
        "PULSAR_ALLOWED_ORIGINS": f'["{base_url}"]',
        "PULSAR_TRUSTED_HOSTS": '["localhost", "127.0.0.1"]',
        "PULSAR_OIDC__ENABLED": "true",
        "PULSAR_OIDC__BASE_URL": base_url,
        "PULSAR_OIDC__PROVIDERS__KEYCLOAK__DISPLAY_NAME": "Keycloak",
        "PULSAR_OIDC__PROVIDERS__KEYCLOAK__DISCOVERY_URL": setup.discovery_url,
        "PULSAR_OIDC__PROVIDERS__KEYCLOAK__CLIENT_ID": setup.client_id,
        "PULSAR_OIDC__PROVIDERS__KEYCLOAK__CLIENT_SECRET": setup.client_secret,
        "PULSAR_OIDC__PROVIDERS__KEYCLOAK__CLAIM_USERNAME": "preferred_username",
    }

    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "pulsar_relay.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(relay_port),
            "--log-level",
            "warning",
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        deadline = time.time() + 30
        while time.time() < deadline:
            try:
                with httpx.Client(timeout=1.0) as c:
                    if c.get(f"{base_url}/health").status_code == 200:
                        break
            except Exception:
                pass
            time.sleep(0.3)
        else:
            stdout, stderr = proc.communicate(timeout=2)
            pytest.fail(f"Relay subprocess did not start.\nstdout={stdout!r}\nstderr={stderr!r}")

        yield {"base_url": base_url, "keycloak": setup}
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
