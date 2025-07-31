"""Integration tests for the Pulsar ARC (Advanced Resource Connector) job runner.

These tests verify that the ARC endpoint URL and OIDC provider selection logic works correctly when queuing jobs. They
do not test actual job execution, as that is covered by Pulsar's own tests.
"""

import json
import string
import tempfile
import threading
from functools import lru_cache
from typing import Optional
from unittest.mock import patch

from sqlalchemy.orm import object_session

from galaxy.jobs import (
    JobDestination,
    JobWrapper,
)
from galaxy.jobs.runners.pulsar import PulsarARCJobRunner
from galaxy.tool_util.verify.interactor import GalaxyInteractorApi
from galaxy_test.base.api import ApiTestInteractor
from galaxy_test.base.api_util import get_admin_api_key
from galaxy_test.base.env import target_url_parts
from galaxy_test.base.populators import DatasetPopulator
from .job_resource_rules.test_pulsar_arc import test_pulsar_arc_set_job_destination as set_job_destination
from .oidc.test_auth_oidc import (
    AbstractTestCases as OIDCAbstractTestCases,
    KEYCLOAK_TEST_PASSWORD,
    KEYCLOAK_TEST_USERNAME,
)

JOB_CONFIG_FILE = """
execution:
  default: arc
  environments:
    arc:
      runner: dynamic
      url: ${galaxy_url}
      type: python
      function: test_pulsar_arc
      rules_module: integration.job_resource_rules
runners:
  arc_runner:
      load: galaxy.jobs.runners.pulsar:PulsarARCJobRunner
"""


def job_config(template_str: str, **vars_) -> str:
    """
    Create a temporary job configuration file from the provided template string.
    """
    job_conf_template = string.Template(template_str)
    job_conf_str = job_conf_template.substitute(**vars_)
    with tempfile.NamedTemporaryFile(suffix="_arc_integration_job_conf.yml", mode="w", delete=False) as job_conf:
        job_conf.write(job_conf_str)
    return job_conf.name


job_wrapper_ref: list[JobWrapper] = []  # keeps a reference to the job wrapper for which a job was last queued
job_wrapper_event = threading.Event()  # synchronization event to signal that a job has been queued


def set_job_wrapper(job_wrapper: JobWrapper) -> None:
    """
    Store a job wrapper reference.
    """
    job_wrapper_ref[:] = [job_wrapper]


def get_job_wrapper() -> Optional[JobWrapper]:
    """
    Return the last stored job wrapper reference (if any).
    """
    return job_wrapper_ref[0] if job_wrapper_ref else None


def queue_job(self, job_wrapper: JobWrapper) -> None:
    """
    Override the `queue_job()` method of the parent class of the Pulsar ARC job runner.

    Fails job queueing and tracks the job wrapper representing the job which should have been queued. Used to test that
    the logic overriding the job destination parameters works correctly.
    """
    set_job_wrapper(job_wrapper)
    job_wrapper_event.set()
    raise Exception("Job queueing failed for testing purposes. This is expected.")


@patch.object(PulsarARCJobRunner.__mro__[1], "queue_job", new=queue_job)
class TestArcPulsarIntegration(OIDCAbstractTestCases.BaseKeycloakIntegrationTestCase):
    """
    Integration test verifying the logic that selects an ARC endpoint URL and an OIDC provider.
    """

    dataset_populator: DatasetPopulator
    framework_tool_and_types = True

    _user_api_key: Optional[str] = None

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        """
        Inject job configuration file tailored for this test case in the Galaxy configuration.
        """
        super().handle_galaxy_config_kwds(config)
        host, port, url = target_url_parts()
        config["job_config_file"] = job_config(JOB_CONFIG_FILE, galaxy_url=url)

    # login just once, even if the method is called multiple times
    @lru_cache(maxsize=1)  # noqa: B019 (bounded cache size)
    def _login_via_keycloak(self, *args, **kwargs):
        """
        Override parent login method to log-in via Keycloak just once and to override the default Galaxy interactor.

        Normally, one would log in within the `setUpClass()` method and call it a day, but since `_login_via_keycloak()`
        is not a class method, this workaround is needed.
        """
        session, response = super()._login_via_keycloak(
            KEYCLOAK_TEST_USERNAME, KEYCLOAK_TEST_PASSWORD, save_cookies=True
        )
        api_interactor = GalaxyInteractorApi(
            galaxy_url=self.url,
            master_api_key=get_admin_api_key(),
            test_user="gxyuser@galaxy.org",
            # email for `KEYCLOAK_TEST_USERNAME`, defined in test/integration/oidc/galaxy-realm-export.json
        )
        self._user_api_key = api_interactor.api_key
        return session, response

    def setUp(self):
        """
        Log-in via Keycloak (just once), override Galaxy interactor and initialize a dataset populator.
        """
        super().setUp()
        self._login_via_keycloak(KEYCLOAK_TEST_USERNAME, KEYCLOAK_TEST_PASSWORD, save_cookies=True)  # happens just once
        self._galaxy_interactor = ApiTestInteractor(self, api_key=self._user_api_key)
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self._job_wrapper = None

    def tearDown(self):
        self._job_wrapper = None

    def run_job(self) -> Optional[JobWrapper]:
        """
        Run a simple job and return the job wrapper.
        """
        with self.dataset_populator.test_history() as history_id:
            hda = self.dataset_populator.new_dataset(history_id, content="abc")
            self.dataset_populator.run_tool(
                tool_id="cat",
                inputs={
                    "input1": {"src": "hda", "id": hda["id"]},
                },
                history_id=history_id,
            )
            self.dataset_populator.wait_for_history(history_id, timeout=20)
        job_wrapper_event.wait(timeout=1)
        job_wrapper = get_job_wrapper()
        return job_wrapper

    def test_queue_job_url_and_oidc_provider_selection(self):
        """
        Verify that the ARC endpoint URL and OIDC provider selection logic works correctly when queuing jobs.
        """
        set_job_destination(
            JobDestination(
                id="arc",
                name="arc",
                runner="arc_runner",
            )
        )
        job_wrapper = self.run_job()
        assert job_wrapper is not None, "No job wrapper created"
        assert job_wrapper.job_destination.params["arc_url"] is None, "No ARC URL expected"
        assert isinstance(
            job_wrapper.job_destination.params["arc_oidc_token"], str
        ), f"Unexpected type {type(job_wrapper.job_destination.params['arc_oidc_token'])} for OIDC token"
        assert len(job_wrapper.job_destination.params["arc_oidc_token"]) > 0, "Invalid OIDC token"

        set_job_destination(
            JobDestination(
                id="arc",
                name="arc",
                runner="arc_runner",
                params={
                    "arc_url": "https://arc.example.com",
                },
            )
        )
        job_wrapper = self.run_job()
        assert job_wrapper is not None, "No job wrapper created"
        assert job_wrapper.job_destination.params["arc_url"] == "https://arc.example.com", "Unexpected ARC URL"
        assert isinstance(
            job_wrapper.job_destination.params["arc_oidc_token"], str
        ), f"Unexpected type {type(job_wrapper.job_destination.params['arc_oidc_token'])} for OIDC token"
        assert len(job_wrapper.job_destination.params["arc_oidc_token"]) > 0, "Invalid OIDC token"

        set_job_destination(
            JobDestination(
                id="arc",
                name="arc",
                runner="arc_runner",
                params={
                    "arc_oidc_provider": "does_not_exist",
                },
            )
        )
        job_wrapper = self.run_job()
        assert job_wrapper is not None, "No job wrapper created"
        assert job_wrapper.job_destination.params["arc_url"] is None, "No ARC URL expected"
        assert job_wrapper.job_destination.params["arc_oidc_token"] is None, "No OIDC token expected"

        set_job_destination(
            JobDestination(
                id="arc",
                name="arc",
                runner="arc_runner",
                params={
                    "arc_user_preferences_key": "does_not_exist",
                },
            )
        )
        job_wrapper = self.run_job()
        assert job_wrapper is not None, "No job wrapper created"
        assert job_wrapper.job_destination.params["arc_url"] is None, "No ARC URL expected"
        assert isinstance(
            job_wrapper.job_destination.params["arc_oidc_token"], str
        ), f"Unexpected type {type(job_wrapper.job_destination.params['arc_oidc_token'])} for OIDC token"
        assert len(job_wrapper.job_destination.params["arc_oidc_token"]) > 0, "Invalid OIDC token"

        # test parameters defined via extra user preferences
        arc_user_preferences_key = "arc_user_preferences"
        user = job_wrapper.get_job().user
        assert user is not None, "No user associated with job"
        extra_user_preferences = user.extra_preferences
        extra_user_preferences[f"{arc_user_preferences_key}|arc_url"] = "https://arc-from-user-prefs.example.com"
        extra_user_preferences[f"{arc_user_preferences_key}|arc_oidc_provider"] = "keycloak"
        user.preferences["extra_user_preferences"] = json.dumps(extra_user_preferences)
        session = object_session(user)
        assert session is not None, "No database session associated with user"
        session.commit()

        set_job_destination(
            JobDestination(
                id="arc",
                name="arc",
                runner="arc_runner",
                params={
                    "arc_user_preferences_key": "does_not_exist",
                    "arc_url": "https://arc.example.com",
                    "arc_oidc_provider": "does_not_exist",
                },
            )
        )
        job_wrapper = self.run_job()
        assert job_wrapper is not None, "No job wrapper created"
        assert job_wrapper.job_destination.params["arc_url"] == "https://arc.example.com", "Unexpected ARC URL"
        assert job_wrapper.job_destination.params["arc_oidc_token"] is None, "No OIDC token expected"

        set_job_destination(
            JobDestination(
                id="arc",
                name="arc",
                runner="arc_runner",
                params={
                    "arc_user_preferences_key": arc_user_preferences_key,
                    "arc_url": "https://arc.example.com",
                    "arc_oidc_provider": "does_not_exist",
                },
            )
        )
        job_wrapper = self.run_job()
        assert job_wrapper is not None, "No job wrapper created"
        assert (
            job_wrapper.job_destination.params["arc_url"]
            == extra_user_preferences[f"{arc_user_preferences_key}|arc_url"]
        ), "Unexpected ARC URL"
        assert isinstance(
            job_wrapper.job_destination.params["arc_oidc_token"], str
        ), f"Unexpected type {type(job_wrapper.job_destination.params['arc_oidc_token'])} for OIDC token"
        assert len(job_wrapper.job_destination.params["arc_oidc_token"]) > 0, "Invalid OIDC token"
