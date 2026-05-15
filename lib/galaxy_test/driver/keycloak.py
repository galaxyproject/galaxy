"""Shared Keycloak Docker container lifecycle helpers for integration tests.

Two start flavours that share the image + ready-probe + teardown:

* :func:`start_keycloak_https_with_realm` — HTTPS, production mode, realm
  imported from a mounted directory. Used by suites that need Keycloak
  to look the way it does in deployment (TLS + a pre-canned realm).
* :func:`start_keycloak_http_dev` — HTTP, dev mode, no realm import.
  Used by suites that provision the realm dynamically via the admin API
  after Keycloak is up.

Bump :data:`KEYCLOAK_IMAGE` here to update both suites in one place.
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

import httpx

#: Canonical upstream Keycloak image. quay.io is the source-of-truth registry
#: for Keycloak; docker.io/keycloak/keycloak is a mirror.
KEYCLOAK_IMAGE = "quay.io/keycloak/keycloak:26.2"

READY_TIMEOUT_SECONDS = 180


def wait_till_keycloak_ready(
    base_url: str,
    *,
    verify: bool = True,
    timeout: int = READY_TIMEOUT_SECONDS,
) -> None:
    """Poll ``{base_url}/realms/master`` until 200/302 or ``timeout`` elapses.

    Pass ``verify=False`` for the HTTPS dev cert.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with httpx.Client(timeout=2.0, verify=verify) as c:
                r = c.get(f"{base_url}/realms/master")
                if r.status_code in (200, 302):
                    return
        except Exception:
            pass
        time.sleep(2)
    raise RuntimeError(f"Keycloak at {base_url} did not become ready within {timeout}s")


def stop_keycloak_docker(container_name: str) -> None:
    subprocess.run(["docker", "rm", "-f", container_name], check=False)


def start_keycloak_https_with_realm(
    *,
    container_name: str,
    host_port: int,
    cert_and_realm_dir: Path,
    admin_username: str = "admin",
    admin_password: str = "admin",
    image: str = KEYCLOAK_IMAGE,
) -> None:
    """Start Keycloak in production mode with TLS + realm import.

    ``cert_and_realm_dir`` must contain ``keycloak-server.crt.pem``,
    ``keycloak-server.key.pem``, and a ``*-realm.json`` file; the
    directory is mounted at ``/opt/keycloak/data/import`` and Keycloak
    consumes all three on startup.
    """
    subprocess.check_call(
        [
            "docker",
            "run",
            "-d",
            "--rm",
            "--name",
            container_name,
            "-p",
            f"{host_port}:8443",
            "-v",
            f"{cert_and_realm_dir}:/opt/keycloak/data/import",
            "-e",
            f"KC_BOOTSTRAP_ADMIN_USERNAME={admin_username}",
            "-e",
            f"KC_BOOTSTRAP_ADMIN_PASSWORD={admin_password}",
            "-e",
            "KC_HOSTNAME_STRICT=false",
            image,
            "start",
            "--import-realm",
            "--https-certificate-file=/opt/keycloak/data/import/keycloak-server.crt.pem",
            "--https-certificate-key-file=/opt/keycloak/data/import/keycloak-server.key.pem",
        ]
    )
    wait_till_keycloak_ready(f"https://localhost:{host_port}", verify=False)


def start_keycloak_http_dev(
    *,
    container_name: str,
    host_port: int,
    admin_username: str = "admin",
    admin_password: str = "adminpassword",
    image: str = KEYCLOAK_IMAGE,
) -> None:
    """Start Keycloak in dev mode with HTTP only.

    For suites that provision the realm + clients + users dynamically via
    the admin API after the server is up. No volume mount needed.
    """
    subprocess.check_call(
        [
            "docker",
            "run",
            "-d",
            "--rm",
            "--name",
            container_name,
            "-p",
            f"{host_port}:8080",
            "-e",
            f"KC_BOOTSTRAP_ADMIN_USERNAME={admin_username}",
            "-e",
            f"KC_BOOTSTRAP_ADMIN_PASSWORD={admin_password}",
            "-e",
            "KC_HTTP_ENABLED=true",
            "-e",
            "KC_HOSTNAME_STRICT=false",
            "-e",
            "KC_HOSTNAME_STRICT_HTTPS=false",
            image,
            "start-dev",
            "--http-port=8080",
        ]
    )
    wait_till_keycloak_ready(f"http://localhost:{host_port}")
