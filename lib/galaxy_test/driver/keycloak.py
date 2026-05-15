"""Shared Keycloak Docker container lifecycle helpers for integration tests.

Two start flavours that share the image + ready-probe + teardown:

* :func:`start_keycloak_https_with_realm` — HTTPS, production mode, realm
  imported into a prebuilt local image. Used by suites that need Keycloak
  to look the way it does in deployment (TLS + a pre-canned realm).
* :func:`start_keycloak_http_dev` — HTTP, dev mode, no realm import.
  Used by suites that provision the realm dynamically via the admin API
  after Keycloak is up.

Bump :data:`KEYCLOAK_IMAGE` here to update both suites in one place.
"""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

import httpx

#: Canonical upstream Keycloak image. quay.io is the source-of-truth registry
#: for Keycloak; docker.io/keycloak/keycloak is a mirror.
KEYCLOAK_IMAGE = "quay.io/keycloak/keycloak:26.2"
#: Local image holding the built server and the imported realm, see
#: :func:`build_keycloak_realm_image`.
KEYCLOAK_REALM_IMAGE = "galaxy-test-keycloak:26.2"
KEYCLOAK_DATA_DIR = "/opt/keycloak/data/import"

READY_TIMEOUT_SECONDS = 180


def keycloak_container_state(container_name: str) -> dict:
    result = subprocess.run(
        ["docker", "inspect", "--format", "{{json .State}}", container_name], capture_output=True, text=True
    )
    if result.returncode:
        return {"Status": "missing", "Error": result.stderr.strip()}
    return json.loads(result.stdout)


def _keycloak_not_ready_error(
    base_url: str, message: str, last_response: str, container_name: str | None
) -> RuntimeError:
    error = f"Keycloak at {base_url} {message}\nLast response: {last_response}"
    if container_name:
        logs = subprocess.run(
            ["docker", "logs", "--timestamps", "--tail", "50", container_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        ).stdout
        state = keycloak_container_state(container_name)
        error = f"{error}\nContainer state: {json.dumps(state)}\nLast container log lines:\n{logs}"
    return RuntimeError(error)


def wait_till_keycloak_ready(
    base_url: str,
    *,
    verify: bool = True,
    timeout: int = READY_TIMEOUT_SECONDS,
    container_name: str | None = None,
) -> None:
    """Poll ``{base_url}/realms/master`` until 200/302 or ``timeout`` elapses.

    Pass ``verify=False`` for the HTTPS dev cert. With ``container_name`` the
    wait fails as soon as that container stops, and the error carries the
    container state and its last log lines.
    """
    deadline = time.time() + timeout
    last_response = "none"
    while time.time() < deadline:
        try:
            with httpx.Client(timeout=2.0, verify=verify) as c:
                r = c.get(f"{base_url}/realms/master")
                if r.status_code in (200, 302):
                    return
                last_response = f"HTTP {r.status_code}"
        except Exception as e:
            last_response = repr(e)
        if container_name and keycloak_container_state(container_name)["Status"] != "running":
            raise _keycloak_not_ready_error(base_url, "stopped before it was ready", last_response, container_name)
        time.sleep(1)
    raise _keycloak_not_ready_error(base_url, f"did not become ready within {timeout}s", last_response, container_name)


def stop_keycloak_docker(container_name: str) -> None:
    subprocess.run(["docker", "rm", "-f", container_name], check=False)


def build_keycloak_realm_image(
    *,
    cert_and_realm_dir: Path,
    realm_file: str,
    admin_username: str,
    admin_password: str,
    image: str = KEYCLOAK_IMAGE,
    tag: str = KEYCLOAK_REALM_IMAGE,
) -> str:
    """Build the server and import the realm once, into a local image.

    A plain ``start --import-realm`` does both in every container and also
    creates the database schema, which takes minutes on a busy runner.
    Docker's build cache makes this a no-op once the image exists.
    """
    dockerfile = f"""FROM {image}
COPY {realm_file} keycloak-server.crt.pem keycloak-server.key.pem {KEYCLOAK_DATA_DIR}/
RUN /opt/keycloak/bin/kc.sh build --db=dev-file \\
    && KC_BOOTSTRAP_ADMIN_USERNAME={admin_username} KC_BOOTSTRAP_ADMIN_PASSWORD={admin_password} \\
    /opt/keycloak/bin/kc.sh import --optimized --file {KEYCLOAK_DATA_DIR}/{realm_file}
"""
    subprocess.run(
        ["docker", "build", "--quiet", "--tag", tag, "--file", "-", str(cert_and_realm_dir)],
        input=dockerfile,
        text=True,
        check=True,
        stdout=subprocess.DEVNULL,
    )
    return tag


def start_keycloak_https_with_realm(
    *,
    container_name: str,
    host_port: int,
    cert_and_realm_dir: Path,
    realm_file: str,
    admin_username: str = "admin",
    admin_password: str = "admin",
    image: str = KEYCLOAK_IMAGE,
) -> None:
    """Start Keycloak in production mode with TLS and an imported realm.

    ``cert_and_realm_dir`` must contain ``keycloak-server.crt.pem``,
    ``keycloak-server.key.pem`` and ``realm_file``; all three are baked
    into the image :func:`build_keycloak_realm_image` builds.

    The container is started without ``--rm`` so one that exits early keeps
    its logs; :func:`stop_keycloak_docker` removes it. ``docker run`` can
    fail after creating the container, so register that cleanup before
    calling this.
    """
    realm_image = build_keycloak_realm_image(
        cert_and_realm_dir=cert_and_realm_dir,
        realm_file=realm_file,
        admin_username=admin_username,
        admin_password=admin_password,
        image=image,
    )
    subprocess.check_call(
        [
            "docker",
            "run",
            "-d",
            "--name",
            container_name,
            "-p",
            f"{host_port}:8443",
            "-e",
            "KC_HOSTNAME_STRICT=false",
            realm_image,
            "start",
            "--optimized",
            f"--https-certificate-file={KEYCLOAK_DATA_DIR}/keycloak-server.crt.pem",
            f"--https-certificate-key-file={KEYCLOAK_DATA_DIR}/keycloak-server.key.pem",
        ]
    )
    wait_till_keycloak_ready(f"https://localhost:{host_port}", verify=False, container_name=container_name)


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
