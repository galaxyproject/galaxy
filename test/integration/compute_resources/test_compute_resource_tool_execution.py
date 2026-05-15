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

import threading
from pathlib import Path
from typing import (
    Any,
    ClassVar,
    Optional,
)

import httpx
import pytest
from pulsar_relay_client import (
    CredentialsFile,
    RelayDeviceFlowAuthenticator,
)
from sqlalchemy import select

from galaxy import model
from galaxy.util.sockets import unused_port
from galaxy_test.base import api_asserts
from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util
from ._harnesses import (
    bring_up_keycloak,
    bring_up_pulsar,
    bring_up_relay,
    KeycloakHandle,
    PulsarHandle,
    RelayHandle,
    teardown_keycloak_docker,
    teardown_subprocess,
)
from ._keycloak_bootstrap import (
    KeycloakSetup,
    provision,
)
from ._keycloak_login import login_via_keycloak

# ``pulsar_relay`` is the *server* package launched as a subprocess by
# ``bring_up_relay``; ``pulsar_relay_client`` (imported above) is a separate
# package. Skip cleanly when the server isn't installed rather than letting
# the uvicorn subprocess fail with an unhelpful import error.
pytest.importorskip("pulsar_relay")

pytestmark = pytest.mark.e2e

HERE = Path(__file__).parent
JOB_CONF_TEMPLATE = HERE / "job_conf.yml.template"
TPV_CONFIG_TEMPLATE = HERE / "tpv_config.yml.template"
PULSAR_APP_TEMPLATE = HERE / "pulsar_app.yml.template"


@integration_util.skip_unless_docker()
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
    _secondary_refresh_token: ClassVar[str]
    _compute_resource_manager_name: ClassVar[str]
    _resource_id: ClassVar[Optional[int]] = None  # genuinely None until setUp() inserts the row
    _tmp_dir: ClassVar[Path]

    # --- IntegrationTestCase hooks ------------------------------------------

    @classmethod
    def _prepare_galaxy(cls) -> None:
        # IntegrationTestCase set up ``_test_driver`` before calling us; its
        # ``galaxy_test_tmp_dir`` is per-class and torn down by the parent's
        # ``tearDownClass``. Use it for Pulsar's staging + rendered configs.
        cls._tmp_dir = Path(cls._test_driver.galaxy_test_tmp_dir) / "compute_resources"
        cls._tmp_dir.mkdir(parents=True, exist_ok=True)

        cls._keycloak = bring_up_keycloak(
            port=unused_port(),
            container_name=f"{cls.__name__}_keycloak",
        )
        # Reserve the relay port up-front so the keycloak client registration
        # can point its redirect_uri at the right callback before the relay
        # subprocess actually starts.
        relay_port = unused_port()
        relay_base_url = f"http://localhost:{relay_port}"
        keycloak_setup = cls._provision_keycloak(relay_base_url=relay_base_url)
        cls._relay = bring_up_relay(
            port=relay_port,
            base_url=relay_base_url,
            keycloak_setup=keycloak_setup,
        )
        tokens = cls._drive_device_flow(keycloak_setup, client_hint="compute-resource-tool-execution")
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

    def setUp(self) -> None:
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        cls = type(self)
        if cls._resource_id is not None:
            return
        assert cls._relay is not None
        # Run Galaxy's production bootstrap path end-to-end through its FastAPI
        # endpoints — exercising ``ComputeResourceManager.complete_registration``
        # (token-exchange → sub-claim validation → topic pinning → DB insert →
        # vault write) rather than reproducing those steps from the test side.
        reg_resp = self.dataset_populator._post("compute_resources/registrations", data={}, json=True)
        api_asserts.assert_status_code_is_ok(reg_resp)
        bootstrap_token = reg_resp.json()["bootstrap_token"]

        complete_resp = self.dataset_populator._post(
            "compute_resources/registrations/complete",
            data={
                "bootstrap_token": bootstrap_token,
                "refresh_token": cls._secondary_refresh_token,
                "relay_url": cls._relay.base_url,
                "manager_name": cls._compute_resource_manager_name,
            },
            json=True,
        )
        api_asserts.assert_status_code_is_ok(complete_resp)
        cls._resource_id = complete_resp.json()["id"]

    @classmethod
    def tearDownClass(cls) -> None:
        # Stop the integration-test subprocesses before Galaxy's teardown (which calls
        # into the model session). Order matters: Pulsar first so the relay
        # has no lingering long-polls, then the relay, then Keycloak.
        teardown_subprocess(cls._pulsar.process if cls._pulsar is not None else None, "pulsar")
        teardown_subprocess(cls._relay.process if cls._relay is not None else None, "relay")
        if cls._keycloak is not None:
            teardown_keycloak_docker(cls._keycloak.container_name)
        super().tearDownClass()

    # --- Sub-fixtures -------------------------------------------------------

    @classmethod
    def _provision_keycloak(cls, *, relay_base_url: str) -> KeycloakSetup:
        assert cls._keycloak is not None
        callback = f"{relay_base_url}/auth/oidc/keycloak/callback"
        return provision(redirect_uris=[callback], setup=KeycloakSetup(base_url=cls._keycloak.base_url))

    @classmethod
    def _drive_device_flow(cls, keycloak_setup: KeycloakSetup, *, client_hint: str) -> dict[str, Any]:
        """Drive RFC 8628 device flow via ``pulsar_relay_client``, completing
        the Keycloak operator login automatically from a worker thread.

        ``RelayDeviceFlowAuthenticator``'s ``on_user_code`` hook lets us
        substitute the human-points-a-browser step with ``login_via_keycloak``
        against the same Keycloak the relay's OIDC provider is wired to.
        """
        assert cls._relay is not None
        relay_url = cls._relay.base_url
        cred_path = cls._tmp_dir / "device_flow_credentials.json"
        operator_error: list[Exception] = []
        op_thread: list[threading.Thread] = []

        def on_user_code(verification_uri_complete: str, user_code: str) -> None:
            def operator() -> None:
                try:
                    with httpx.Client(timeout=10.0, follow_redirects=False) as op:
                        start = op.get(
                            f"{relay_url}/auth/oidc/keycloak/login",
                            params={"device_user_code": user_code},
                        )
                        assert start.status_code == 302, start.text
                        final = login_via_keycloak(
                            authorization_url=start.headers["location"],
                            username=keycloak_setup.user_username,
                            password=keycloak_setup.user_password,
                            follow_relay_callback=True,
                        )
                        assert final.status_code == 200
                except Exception as exc:
                    operator_error.append(exc)

            t = threading.Thread(target=operator, daemon=True)
            t.start()
            op_thread.append(t)

        flow = RelayDeviceFlowAuthenticator(
            relay_url=relay_url,
            credentials_file=CredentialsFile(str(cred_path)),
            client_hint=client_hint,
            pair=True,
            on_user_code=on_user_code,
        )
        creds = flow.run()
        if op_thread:
            op_thread[0].join(timeout=10)
        if operator_error:
            raise operator_error[0]
        return creds

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
