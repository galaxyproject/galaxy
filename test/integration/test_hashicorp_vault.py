"""Integration tests for Hashicorp Vault token renewal using a real Vault Docker container.

Requires Docker to be available. The test starts a hashicorp/vault container in dev mode,
creates a renewable token, and verifies the renewal logic works end-to-end.
"""

import os
import subprocess
import tempfile
import threading
import time

import requests

from galaxy.security.vault import (
    _unwrap_vault,
    HashicorpVault,
)
from galaxy.util.wait import wait_on
from galaxy_test.base.populators import CredentialsPopulator
from galaxy_test.driver import integration_util
from galaxy_test.driver.integration_util import (
    docker_rm,
    docker_run,
    skip_unless_docker,
)

VAULT_DEV_ROOT_TOKEN = "vault-integration-test-token"
VAULT_PORT = 18200
VAULT_IMAGE = "hashicorp/vault"
CREDENTIALS_TOOL = "secret_tool"
CREDENTIALS_VARIABLES = [{"name": "server", "value": "http://localhost:8080"}]
CREDENTIALS_SECRETS = [{"name": "username", "value": "user"}, {"name": "password", "value": "pass"}]


class VaultClient:
    """Thin wrapper around the Vault HTTP API for test setup."""

    def __init__(self, addr, token):
        self.addr = addr
        self.session = requests.Session()
        self.session.headers.update(
            {
                "X-Vault-Token": token,
                "Content-Type": "application/json",
            }
        )

    def wait_ready(self, timeout=30):
        def check():
            try:
                self.session.get(f"{self.addr}/v1/sys/health", timeout=2).raise_for_status()
                return True
            except Exception:
                return None

        wait_on(check, "Vault to become ready", timeout)

    def create_policy(self, name, hcl):
        self.session.put(f"{self.addr}/v1/sys/policies/acl/{name}", json={"policy": hcl})

    def create_renewable_token(self, ttl="1h", max_ttl="24h", policies=None):
        result = self.session.post(
            f"{self.addr}/v1/auth/token/create",
            json={
                "ttl": ttl,
                "explicit_max_ttl": max_ttl,
                "renewable": True,
                "policies": policies or ["default"],
            },
        ).json()
        return result["auth"]["client_token"]


def _write_vault_config(vault_addr, vault_token, path_prefix="/galaxy_integration_test"):
    fd, path = tempfile.mkstemp(prefix="vault_hashicorp_integ_", suffix=".yml")
    with os.fdopen(fd, "w") as f:
        f.write(
            f"type: hashicorp\n"
            f"path_prefix: {path_prefix}\n"
            f"vault_address: {vault_addr}\n"
            f"vault_token: {vault_token}\n"
        )
    return path


def _start_vault_container(container_name):
    try:
        docker_rm(container_name)
    except subprocess.CalledProcessError:
        pass
    docker_run(
        VAULT_IMAGE,
        container_name,
        "server",
        "-dev",
        f"-dev-root-token-id={VAULT_DEV_ROOT_TOKEN}",
        "-dev-listen-address=0.0.0.0:8200",
        ports=[(VAULT_PORT, 8200)],
        env_vars={"VAULT_ADDR": "http://0.0.0.0:8200"},
    )
    vault_addr = f"http://127.0.0.1:{VAULT_PORT}"
    client = VaultClient(vault_addr, VAULT_DEV_ROOT_TOKEN)
    client.wait_ready()
    client.create_policy(
        "galaxy",
        r'path "secret/*" { capabilities = ["create","read","update","delete","list"] }',
    )
    return vault_addr, client


@skip_unless_docker()
class TestHashicorpVaultRenewalGalaxyIntegration(integration_util.IntegrationTestCase):
    """Full Galaxy + Vault + Celery Beat integration test.

    Starts a Galaxy instance backed by a Hashicorp Vault Docker container.
    An in-process Celery Beat scheduler fires ``renew_vault_token`` every
    2 s with ``task_always_eager`` so tasks execute immediately in the Beat
    thread via the Galaxy app's DI container.

    The test stores credentials (which write secrets to the vault) via the
    Galaxy API, then verifies the operation still succeeds past the token
    TTL thanks to Beat renewal.
    """

    container_name = "galaxy_test_hashicorp_vault_galaxy"
    vault_addr: str
    vault_config_path: str
    _vault_client: VaultClient
    _vault_token: str
    _beat_service = None
    _beat_thread = None
    RENEWAL_INTERVAL = 2  # seconds

    @classmethod
    def setUpClass(cls):
        cls.vault_addr, cls._vault_client = _start_vault_container(cls.container_name)
        super().setUpClass()
        cls._start_beat()

    @classmethod
    def tearDownClass(cls):
        cls._stop_beat()
        super().tearDownClass()
        docker_rm(cls.container_name)
        if hasattr(cls, "vault_config_path") and os.path.exists(cls.vault_config_path):
            os.unlink(cls.vault_config_path)

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        cls._vault_token = cls._vault_client.create_renewable_token(
            ttl="1h",
            max_ttl="24h",
            policies=["galaxy"],
        )
        cls.vault_config_path = _write_vault_config(
            cls.vault_addr,
            cls._vault_token,
            path_prefix="/galaxy",
        )
        config["vault_config_file"] = cls.vault_config_path
        config["vault_token_renewal_interval"] = cls.RENEWAL_INTERVAL

    def setUp(self):
        super().setUp()
        self.credentials_populator = CredentialsPopulator(self.galaxy_interactor)

    # ---- Beat ----------------------------------------------------------------

    @classmethod
    def _start_beat(cls):
        from celery.beat import Service as BeatService

        from galaxy.celery import celery_app

        module_name = celery_app.trim_module_name("galaxy.celery.tasks")
        schedule = dict(celery_app.conf.beat_schedule or {})
        schedule["renew-vault-token"] = {
            "task": f"{module_name}.renew_vault_token",
            "schedule": cls.RENEWAL_INTERVAL,
        }
        celery_app.conf.beat_schedule = schedule
        celery_app.conf.task_always_eager = True

        cls._beat_service = BeatService(celery_app, max_interval=cls.RENEWAL_INTERVAL)
        cls._beat_thread = threading.Thread(target=cls._beat_service.start, daemon=True)
        cls._beat_thread.start()
        time.sleep(1)

    @classmethod
    def _stop_beat(cls):
        if cls._beat_service:
            cls._beat_service.stop()
        if cls._beat_thread:
            cls._beat_thread.join(timeout=5)
        from galaxy.celery import celery_app

        celery_app.conf.task_always_eager = False

    # ---- helpers -------------------------------------------------------------

    def _swap_token(self, new_token):
        inner = _unwrap_vault(self._app.vault)
        assert isinstance(inner, HashicorpVault)
        inner.client.token = new_token
        inner.vault_token = new_token

    # ---- tests ---------------------------------------------------------------

    def test_beat_renews_token_and_secrets_survive(self):
        """Beat fires renew_vault_token every 2 s, keeping the token alive past its 3 s TTL."""
        # Swap in a short-lived token after Galaxy is running.
        short_token = self._vault_client.create_renewable_token(
            ttl="3s",
            max_ttl="1h",
            policies=["galaxy"],
        )
        self._swap_token(short_token)

        # Store credentials — secrets go to Vault.
        self.credentials_populator.create_credentials(
            tool_id=CREDENTIALS_TOOL,
            variables=CREDENTIALS_VARIABLES,
            secrets=CREDENTIALS_SECRETS,
        )

        # Beat renews every 2 s.  Sleep 4 s — past the 3 s TTL.
        time.sleep(4)

        # Creating credentials again exercises a vault write — this would fail
        # with Forbidden if the token had expired.
        self.credentials_populator.create_credentials(
            tool_id=CREDENTIALS_TOOL,
            variables=CREDENTIALS_VARIABLES,
            secrets=CREDENTIALS_SECRETS,
        )

        self._swap_token(self._vault_token)
