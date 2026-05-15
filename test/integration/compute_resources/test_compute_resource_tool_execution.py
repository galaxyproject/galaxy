"""End-to-end compute-resource tool-execution test.

This is the heavy sibling of ``test_byoc_e2e.py``. It brings up the full
stack — Keycloak (via docker compose) → pulsar-relay (subprocess) →
Pulsar daemon (subprocess) → Galaxy (in-process via
``IntegrationTestCase``) — drives the compute-resource bootstrap, then submits a real
framework tool and asserts that:

1. TPV routes the job to the ``compute_resource`` runner.
2. The multi-tenant runner materialises a client manager bound to the
   compute-resource user's relay + manager_name.
3. The Pulsar daemon picks up the ``job_setup_<manager>`` message,
   executes the tool, and publishes a ``job_status_update_<manager>``
   completion.
4. Galaxy collects the outputs and marks the job ``ok``.

Skipped automatically when Docker / the pulsar-relay checkout / the
pulsar checkout aren't reachable — see the suite README.

This test is intentionally instrumented for debugging. Failures dump the
relay + Pulsar subprocess logs to stdout so a tester can diagnose without
re-running.
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
from pathlib import Path
from typing import (
    ClassVar,
    Optional,
)

import httpx
import pytest
from sqlalchemy import select

from galaxy import model
from galaxy.managers.compute_resources import (
    relay_refresh_token_vault_path,
    STATUS_ACTIVE,
)
from galaxy.security.vault import UserVaultWrapper
from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util
from ._device_flow import drive_device_flow_with_pair
from ._harnesses import (
    bring_up_keycloak,
    bring_up_pulsar,
    bring_up_relay,
    KeycloakHandle,
    PulsarHandle,
    RelayHandle,
    teardown_compose,
    teardown_subprocess,
)
from ._keycloak_bootstrap import (
    KeycloakSetup,
    provision,
)

pytestmark = pytest.mark.e2e

HERE = Path(__file__).parent
COMPOSE_FILE = HERE / "docker-compose.yml"
JOB_CONF_TEMPLATE = HERE / "job_conf.yml.template"
TPV_CONFIG_TEMPLATE = HERE / "tpv_config.yml.template"
PULSAR_APP_TEMPLATE = HERE / "pulsar_app.yml.template"

# --- Helpers (mirrored from conftest so this file is grep-able standalone) ---


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return int(s.getsockname()[1])


def _compose_cmd() -> Optional[list[str]]:
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
    return None


def _docker_running() -> bool:
    docker = shutil.which("docker")
    if docker is None:
        return False
    try:
        subprocess.run([docker, "info"], check=True, capture_output=True, timeout=5)
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False


class TestComputeResourceToolExecution(
    integration_util.IntegrationTestCase,
    integration_util.ConfiguresDatabaseVault,
):
    """Real-tool-on-real-Pulsar compute-resource e2e."""

    framework_tool_and_types = True
    dataset_populator: DatasetPopulator

    # All ClassVars below get populated in ``_prepare_galaxy`` (and are
    # safe to read in the test methods, which only run after that hook).
    # The non-Optional handles default to ``None`` so tearDownClass can
    # short-circuit if bring-up failed partway through.
    _keycloak: ClassVar[Optional[KeycloakHandle]] = None
    _relay: ClassVar[Optional[RelayHandle]] = None
    _pulsar: ClassVar[Optional[PulsarHandle]] = None
    _compose: ClassVar[Optional[list[str]]] = None
    _secondary_refresh_token: ClassVar[str]
    _compute_resource_manager_name: ClassVar[str]
    _resource_id: ClassVar[Optional[int]] = None  # genuinely None until setUp() inserts the row
    _tmp_dir: ClassVar[Path]

    # --- IntegrationTestCase hooks ------------------------------------------

    @classmethod
    def _prepare_galaxy(cls) -> None:
        if not _docker_running():
            pytest.skip("Docker daemon not reachable; skipping compute-resource tool-execution suite.")
        compose = _compose_cmd()
        if compose is None:
            pytest.skip("docker / docker-compose not available")
        cls._compose = compose

        # Per-class working dir for Pulsar's staging/persistence and the
        # rendered job_conf/tpv_config files. ``COMPUTE_RESOURCE_E2E_TMP`` lets a tester
        # pin it to a known path for ad-hoc debugging; otherwise mkdtemp.
        override = os.environ.get("COMPUTE_RESOURCE_E2E_TMP")
        if override:
            cls._tmp_dir = Path(override)
            cls._tmp_dir.mkdir(parents=True, exist_ok=True)
        else:
            import tempfile

            cls._tmp_dir = Path(tempfile.mkdtemp(prefix="compute_resource_e2e_"))

        cls._keycloak = bring_up_keycloak(compose=compose, compose_file=COMPOSE_FILE, free_port=_free_port())
        # Reserve the relay port up-front so the keycloak client registration
        # can point its redirect_uri at the right callback before the relay
        # subprocess actually starts.
        relay_port = _free_port()
        relay_base_url = f"http://localhost:{relay_port}"
        keycloak_setup = cls._provision_keycloak(relay_base_url=relay_base_url)
        cls._relay = bring_up_relay(
            port=relay_port,
            base_url=relay_base_url,
            keycloak_setup=keycloak_setup,
        )
        tokens = drive_device_flow_with_pair(
            cls._relay.base_url, keycloak_setup, client_hint="compute-resource-tool-execution"
        )
        cls._secondary_refresh_token = tokens["refresh_token_secondary"]
        # manager_name = the relay user's username, which Keycloak maps from
        # the OIDC claim_username configured for the relay. We pull it from
        # /auth/me using the access token rather than decoding the JWT here.
        me = httpx.get(
            f"{cls._relay.base_url}/auth/me",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            timeout=5.0,
        )
        me.raise_for_status()
        cls._compute_resource_manager_name = me.json()["username"]

        # Pre-create the topics pulsar will subscribe to. The relay does not
        # auto-create topics on long-poll subscription (only on owner POST),
        # so without this the GET /api/v1/topics/{name} signal we use in
        # bring_up_pulsar would never go 200. Mirrors the
        # ``create_or_verify_topic`` loop Galaxy runs during compute-resource bootstrap.
        cls._pre_create_topics(access_token=tokens["access_token"])

        cls._pulsar = bring_up_pulsar(
            tmp_dir=cls._tmp_dir,
            relay_base_url=cls._relay.base_url,
            manager_name=cls._compute_resource_manager_name,
            primary_token=tokens["refresh_token"],
            access_token=tokens["access_token"],
            app_template=PULSAR_APP_TEMPLATE,
        )
        cls._render_galaxy_config_files()

    @classmethod
    def _pre_create_topics(cls, *, access_token: str) -> None:
        assert cls._relay is not None
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        for prefix in ("job_setup", "job_status_request", "job_kill", "job_status_update"):
            topic_name = f"{prefix}_{cls._compute_resource_manager_name}"
            r = httpx.post(
                f"{cls._relay.base_url}/api/v1/topics",
                headers=headers,
                json={"topic_name": topic_name},
                timeout=5.0,
            )
            if r.status_code not in (200, 201, 400, 409):
                pytest.fail(f"Failed to pre-create relay topic {topic_name}: HTTP {r.status_code} {r.text}")

    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        super().handle_galaxy_config_kwds(config)
        assert cls._relay is not None
        config["enable_compute_resources"] = True
        config["compute_resource_relay_url"] = cls._relay.base_url
        config["job_config_file"] = str(cls._tmp_dir / "job_conf.yml")
        # Pulsar pulls staged files from this URL — must point at the live
        # IntegrationTestCase web port, not the default 8080.
        config["galaxy_infrastructure_url"] = "http://localhost:$GALAXY_WEB_PORT"
        # Compute resources store the relay refresh token in the user vault.
        cls._configure_database_vault(config)
        config["enable_celery_tasks"] = False
        config["metadata_strategy"] = "directory"

    @classmethod
    def _configure_app(cls) -> None:
        super()._configure_app()
        # Galaxy is now up. Insert the compute resource + vault secret for
        # whichever user dataset_populator will end up running as.
        # We resolve that user lazily in setUp() because dataset_populator
        # provisions on first use.

    def setUp(self) -> None:
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        cls = type(self)
        if cls._resource_id is not None:
            return
        assert cls._relay is not None
        # First test: create the resource scoped to the populator's user.
        user_id_encoded = self.dataset_populator.user_id()
        user_id = self._app.security.decode_id(user_id_encoded)
        user = self._app.model.session.get(model.User, user_id)
        assert user is not None, "expected dataset_populator to provision a user"

        resource = model.ComputeResource(
            user_id=user.id,
            manager_name=cls._compute_resource_manager_name,
            relay_url=cls._relay.base_url,
            status=STATUS_ACTIVE,
        )
        self._app.model.session.add(resource)
        self._app.model.session.commit()
        cls._resource_id = resource.id

        UserVaultWrapper(self._app.vault, user).write_secret(
            relay_refresh_token_vault_path(resource.id),
            cls._secondary_refresh_token,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        # Stop the integration-test subprocesses before Galaxy's teardown (which calls
        # into the model session). Order matters: Pulsar first so the relay
        # has no lingering long-polls, then the relay, then Keycloak.
        teardown_subprocess(cls._pulsar.process if cls._pulsar is not None else None, "pulsar")
        teardown_subprocess(cls._relay.process if cls._relay is not None else None, "relay")
        if cls._keycloak is not None and cls._compose is not None:
            teardown_compose(
                compose=cls._compose,
                compose_file=COMPOSE_FILE,
                compose_env=cls._keycloak.compose_env,
            )
        super().tearDownClass()

    # --- Sub-fixtures -------------------------------------------------------

    @classmethod
    def _provision_keycloak(cls, *, relay_base_url: str) -> KeycloakSetup:
        assert cls._keycloak is not None
        callback = f"{relay_base_url}/auth/oidc/keycloak/callback"
        return provision(redirect_uris=[callback], setup=KeycloakSetup(base_url=cls._keycloak.base_url))

    @classmethod
    def _render_galaxy_config_files(cls) -> None:
        # Pulsar's staging_directory must equal the destination's
        # jobs_directory so the tool_script paths Galaxy bakes into command_line
        # resolve on the pulsar side. Use str.replace rather than .format here
        # because the TPV file is full of literal ``{app...}`` rule expressions.
        jobs_dir = cls._tmp_dir / "pulsar" / "staging"
        tpv_path = cls._tmp_dir / "tpv_config.yml"
        tpv_path.write_text(TPV_CONFIG_TEMPLATE.read_text().replace("__JOBS_DIR__", str(jobs_dir)))

        job_conf_path = cls._tmp_dir / "job_conf.yml"
        job_conf_path.write_text(JOB_CONF_TEMPLATE.read_text().format(tpv_config_file=str(tpv_path)))

    # --- The test itself ----------------------------------------------------

    def test_framework_tool_runs_via_compute_resource(self) -> None:
        """Submit ``environment_variables`` and verify it completes via the
        ``compute_resource`` runner."""
        cls = type(self)
        assert cls._resource_id is not None
        with self.dataset_populator.test_history() as history_id:
            response = self.dataset_populator.run_tool(
                "environment_variables",
                inputs={"inttest": "3"},
                history_id=history_id,
            )
            self.dataset_populator.wait_for_job(response["jobs"][0]["id"], assert_ok=True)
            job_id_encoded = response["jobs"][0]["id"]
            job_id = self._app.security.decode_id(job_id_encoded)
            job = self._app.model.session.scalars(select(model.Job).filter_by(id=job_id)).one()
            assert (
                job.job_runner_name == "compute_resource"
            ), f"job ran on {job.job_runner_name!r}, expected compute_resource"
            assert job.state == model.Job.states.OK
            # The TPV rule should have injected the resource id into the
            # destination params.
            params = job.destination_params or {}
            assert str(params.get("compute_resource_id")) == str(cls._resource_id)
            assert params.get("manager") == cls._compute_resource_manager_name
