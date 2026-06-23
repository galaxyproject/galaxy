import contextlib
import importlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
import uuid
from queue import Queue
from typing import ClassVar

import pytest

from galaxy import model
from galaxy.jobs.job_destination import JobDestination
from galaxy.jobs.runners import htcondor
from galaxy.util import bunch
from galaxy_test.base.populators import (
    DatasetPopulator,
    skip_without_tool,
)
from galaxy_test.driver import integration_util

LIVE_FAKE_MODULE_PATH = os.path.join(os.path.dirname(__file__), "htcondor_fake")


def _fake_job_conf() -> str:
    """Job config for the fake end-to-end test: in-process htcondor, no htcondor_config."""
    return """
runners:
  local:
    load: galaxy.jobs.runners.local:LocalJobRunner
    workers: 1
  htcondor:
    load: galaxy.jobs.runners.htcondor:HTCondorJobRunner
    workers: 1
execution:
  default: htcondor_environment
  environments:
    htcondor_environment:
      runner: htcondor
    local_environment:
      runner: local
tools:
  - id: __DATA_FETCH__
    environment: local_environment
"""


# ---------------------------------------------------------------------------
# Docker-based minicondor container tests
# ---------------------------------------------------------------------------

# Override with GALAXY_TEST_HTCONDOR_IMAGE to use a different image.
HTCONDOR_MINI_IMAGE = os.environ.get(
    "GALAXY_TEST_HTCONDOR_IMAGE",
    "htcondor/mini:el9@sha256:32eae7e6dd294e52668045ce4a7f58a550fa9de29930e7c920ee6c4856eb2030",
)

# Seconds to wait for the schedd to become reachable after container start.
HTCONDOR_STARTUP_TIMEOUT = 120


def _container_condor_config() -> str:
    """Condor config mounted into the minicondor container.

    Makes all daemons listen on every interface so the host htcondor2 library
    can reach the schedd via the Docker bridge IP.  We keep the container's
    default IDTOKENS-based security model intact; the host authenticates with
    a token generated inside the container (see ``start_htcondor_docker``).

    The negotiator interval is reduced so jobs are matched quickly in tests
    (the default 60 s cycle would exceed the test timeout).
    """
    return textwrap.dedent("""
        # Listen on all interfaces — required for the host to reach the container
        # via its Docker bridge IP rather than only 127.0.0.1.
        NETWORK_INTERFACE = *

        # Match jobs quickly so tests finish well within their timeout.
        NEGOTIATOR_INTERVAL = 5
        """).lstrip()


def _host_condor_config(collector_addr: str, token_dir: str) -> str:
    """Minimal condor config for the host-side htcondor2 subprocess client.

    Points the htcondor2 library at the containerised collector and provides
    the path to the IDTOKEN that was generated inside the container.
    """
    return textwrap.dedent(f"""
        COLLECTOR_HOST      = {collector_addr}
        CONDOR_HOST         = {collector_addr.split(":")[0]}
        SEC_TOKEN_DIRECTORY = {token_dir}
        """).lstrip()


def _container_job_conf(collector_addr: str, host_config_path: str) -> str:
    return textwrap.dedent(f"""
        runners:
          local:
            load: galaxy.jobs.runners.local:LocalJobRunner
            workers: 1
          htcondor:
            load: galaxy.jobs.runners.htcondor:HTCondorJobRunner
            workers: 1
        execution:
          default: htcondor_environment
          environments:
            htcondor_environment:
              runner: htcondor
              htcondor_collector: "{collector_addr}"
              htcondor_config: "{host_config_path}"
            local_environment:
              runner: local
        tools:
          - id: __DATA_FETCH__
            environment: local_environment
        """).lstrip()


def _two_cluster_job_conf(
    collector_addr_a: str,
    host_config_path_a: str,
    collector_addr_b: str,
    host_config_path_b: str,
) -> str:
    """Job config routing tools across two independent HTCondor clusters.

    All tools default to cluster A.  ``checksum`` is explicitly routed to
    cluster B so ``test_htcondor_docker_job_cluster_b`` can verify that each
    cluster receives its own jobs independently.
    """
    return textwrap.dedent(f"""
        runners:
          local:
            load: galaxy.jobs.runners.local:LocalJobRunner
            workers: 1
          htcondor:
            load: galaxy.jobs.runners.htcondor:HTCondorJobRunner
            workers: 1
        execution:
          default: htcondor_cluster_a
          environments:
            htcondor_cluster_a:
              runner: htcondor
              htcondor_collector: "{collector_addr_a}"
              htcondor_config: "{host_config_path_a}"
            htcondor_cluster_b:
              runner: htcondor
              htcondor_collector: "{collector_addr_b}"
              htcondor_config: "{host_config_path_b}"
            local_environment:
              runner: local
        tools:
          - id: __DATA_FETCH__
            environment: local_environment
          - id: checksum
            environment: htcondor_cluster_b
        """).lstrip()


def start_htcondor_docker(container_name: str, jobs_directory: str) -> tuple[str, str, str, str]:
    """Start an htcondor/mini container and return (container_config_path, host_config_path, collector_addr, token_dir).

    The container is started without port mapping.  After it is running, its
    Docker bridge IP is obtained via ``docker inspect`` and used as the
    collector address.  This avoids the CEDAR address-embedding problem that
    occurs with port mapping.

    Authentication uses the container's default IDTOKENS model.  Once the
    schedd is ready, the host OS user is added to the container's
    ``/etc/passwd`` (so HTCondor can setuid to the right UID when running
    jobs), and an IDTOKEN is generated inside the container and written to a
    temporary directory on the host.  The host-side htcondor2 subprocess
    client uses this token to authenticate with the container's schedd.

    The Galaxy job-working directory is bind-mounted at the same path inside
    the container so job scripts written by Galaxy are accessible to the startd.
    """
    with tempfile.NamedTemporaryFile(suffix="_container_condor_config.local", mode="w", delete=False) as f:
        f.write(_container_condor_config())
        container_config_path = f.name

    subprocess.check_call(
        [
            "docker",
            "run",
            "--detach",
            "--name",
            container_name,
            "--rm",
            "-v",
            f"{jobs_directory}:{jobs_directory}",
            "-v",
            f"{container_config_path}:/etc/condor/condor_config.local",
            HTCONDOR_MINI_IMAGE,
        ]
    )

    # Obtain the container's Docker bridge IP — reachable from the host.
    container_ip = subprocess.check_output(
        [
            "docker",
            "inspect",
            "-f",
            "{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}",
            container_name,
        ],
        text=True,
    ).strip()
    collector_addr = f"{container_ip}:9618"

    # Wait for the schedd — this also ensures the pool password (used to sign
    # IDTOKENS) has been initialised by condor_master.
    _wait_for_htcondor_schedd(container_name)

    # Determine which username to use for the job identity.  HTCondor's schedd
    # validates that the submitting user exists in the container's /etc/passwd
    # and the startd setuid()s to that UID when running the job.  The job
    # working directories are owned by the host user's UID, so the job process
    # must run as the same numeric UID.
    #
    # Strategy: look up the host UID in the container's passwd database.  If a
    # user already has that UID (e.g. "restd" in htcondor/mini:el9), use that
    # username for the token identity — the numeric UID is the same as the host
    # user, so the job can write to the bind-mounted directories.  If no
    # container user has the host UID, add an entry for the host username.
    host_uid = os.getuid()
    host_gid = os.getgid()
    host_username = subprocess.check_output(["id", "-un"], text=True).strip()
    result = subprocess.run(
        ["docker", "exec", container_name, "getent", "passwd", str(host_uid)],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        token_username = result.stdout.split(":")[0]
    else:
        # The host user is not in the container's passwd database.  Append a
        # minimal entry so HTCondor can validate the identity and setuid to the
        # right UID.  Pipe via stdin to tee to avoid any shell-quoting concerns.
        passwd_line = f"{host_username}:x:{host_uid}:{host_gid}:{host_username}:/tmp:/bin/sh\n"
        subprocess.run(
            ["docker", "exec", "-i", container_name, "tee", "-a", "/etc/passwd"],
            input=passwd_line,
            text=True,
            check=True,
            stdout=subprocess.DEVNULL,
        )
        token_username = host_username

    # Generate an IDTOKEN inside the container for the resolved identity.
    # The container signs the token with its pool password; the host client
    # presents the token and the schedd verifies it — no password exchange needed.
    token_identity = f"{token_username}@galaxy_test"
    token_content = subprocess.check_output(
        [
            "docker",
            "exec",
            container_name,
            "condor_token_create",
            "-identity",
            token_identity,
        ],
        text=True,
    ).strip()
    token_dir = tempfile.mkdtemp(prefix="htcondor_tokens_")
    os.chmod(token_dir, 0o700)
    token_path = os.path.join(token_dir, "galaxy_test")
    with open(token_path, "w") as fh:
        fh.write(token_content + "\n")
    os.chmod(token_path, 0o600)

    with tempfile.NamedTemporaryFile(suffix="_host_condor_config", mode="w", delete=False) as f:
        f.write(_host_condor_config(collector_addr, token_dir))
        host_config_path = f.name

    return container_config_path, host_config_path, collector_addr, token_dir


def stop_htcondor_docker(
    container_name: str,
    container_config_path: str | None = None,
    host_config_path: str | None = None,
    token_dir: str | None = None,
) -> None:
    """Stop the minicondor container and clean up temporary config files."""
    if container_name:
        subprocess.call(["docker", "rm", "-f", container_name])
    if container_config_path:
        with contextlib.suppress(OSError):
            os.remove(container_config_path)
    if host_config_path:
        with contextlib.suppress(OSError):
            os.remove(host_config_path)
    if token_dir:
        with contextlib.suppress(OSError):
            os.remove(os.path.join(token_dir, "galaxy_test"))
        with contextlib.suppress(OSError):
            os.rmdir(token_dir)


def _condor_history_count(container_name: str) -> int:
    """Return the number of jobs recorded in the container's condor history.

    Uses ``condor_history -format`` so the output contains exactly one line
    per completed job, with no header — making the count unambiguous.
    """
    result = subprocess.run(
        [
            "docker",
            "exec",
            container_name,
            "condor_history",
            "-format",
            "%d\n",
            "ClusterId",
        ],
        capture_output=True,
        text=True,
    )
    return len([line for line in result.stdout.splitlines() if line.strip()])


def _wait_for_htcondor_schedd(container_name: str, timeout: int = HTCONDOR_STARTUP_TIMEOUT) -> None:
    """Poll until the schedd inside the container reports at least one slot."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = subprocess.run(
            ["docker", "exec", container_name, "condor_status", "-schedd"],
            capture_output=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            return
        time.sleep(2)
    raise RuntimeError(f"HTCondor schedd in container {container_name!r} did not become ready within {timeout}s")


@integration_util.skip_unless_docker()
class TestHTCondorContainerJob(integration_util.IntegrationTestCase):
    """End-to-end tests using a real HTCondor minicondor Docker container.

    These tests submit actual Galaxy jobs to the htcondor runner, which in turn
    talks to a real HTCondor schedd running inside ``htcondor/mini``.  They
    validate the full submit → monitor → finish cycle and the cancel path
    against the real htcondor2 Python API, complementing the unit-style tests
    that use the fake htcondor2 stub.

    Prerequisites
    -------------
    * Docker must be available (tests are skipped otherwise).

    Environment variables
    ---------------------
    ``GALAXY_TEST_HTCONDOR_IMAGE``
        Override the Docker image (default: pinned ``htcondor/mini:el9`` digest).
    """

    framework_tool_and_types = True
    dataset_populator: DatasetPopulator
    _container_name: ClassVar[str] = "galaxy_htcondor_integration_test"
    _container_name_b: ClassVar[str] = "galaxy_htcondor_integration_test_b"
    _jobs_directory: ClassVar[str]
    _container_config_path: ClassVar[str]
    _host_config_path: ClassVar[str]
    _collector_addr: ClassVar[str]
    _token_dir: ClassVar[str]
    _container_config_path_b: ClassVar[str]
    _host_config_path_b: ClassVar[str]
    _collector_addr_b: ClassVar[str]
    _token_dir_b: ClassVar[str]

    @classmethod
    def setUpClass(cls) -> None:
        suffix = f"{os.getpid()}_{uuid.uuid4().hex[:8]}"
        cls._container_name = f"galaxy_htcondor_integration_test_{suffix}"
        cls._container_name_b = f"galaxy_htcondor_integration_test_b_{suffix}"
        cls._jobs_directory = tempfile.mkdtemp(prefix="htcondor_container_jobs_")
        os.chmod(cls._jobs_directory, 0o777)
        for sub in ("files", "new_files"):
            subdir = os.path.join(cls._jobs_directory, sub)
            os.makedirs(subdir, exist_ok=True)
            os.chmod(subdir, 0o777)

        # Start both containers in parallel to reduce wall-clock setup time.
        _results: dict[str, tuple] = {}
        _errors: dict[str, Exception] = {}

        def _start(label: str, name: str) -> None:
            try:
                _results[label] = start_htcondor_docker(name, cls._jobs_directory)
            except Exception as exc:
                _errors[label] = exc

        threads = [
            threading.Thread(target=_start, args=("a", cls._container_name), daemon=True),
            threading.Thread(target=_start, args=("b", cls._container_name_b), daemon=True),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        if _errors:
            cls._cleanup_htcondor_resources()
            raise RuntimeError(f"HTCondor container startup failed: {_errors}")

        (
            cls._container_config_path,
            cls._host_config_path,
            cls._collector_addr,
            cls._token_dir,
        ) = _results["a"]
        (
            cls._container_config_path_b,
            cls._host_config_path_b,
            cls._collector_addr_b,
            cls._token_dir_b,
        ) = _results["b"]

        # Remove any fake htcondor2 stub so the real library is imported.
        sys.modules.pop("htcondor2", None)
        if LIVE_FAKE_MODULE_PATH in sys.path:
            sys.path.remove(LIVE_FAKE_MODULE_PATH)

        try:
            super().setUpClass()
        except BaseException:
            cls._cleanup_htcondor_resources()
            raise

    @classmethod
    def tearDownClass(cls) -> None:
        try:
            super().tearDownClass()
        finally:
            cls._cleanup_htcondor_resources()

    @classmethod
    def _cleanup_htcondor_resources(cls) -> None:
        if hasattr(cls, "_container_name"):
            stop_htcondor_docker(
                cls._container_name,
                getattr(cls, "_container_config_path", None),
                getattr(cls, "_host_config_path", None),
                getattr(cls, "_token_dir", None),
            )
        if hasattr(cls, "_container_name_b"):
            stop_htcondor_docker(
                cls._container_name_b,
                getattr(cls, "_container_config_path_b", None),
                getattr(cls, "_host_config_path_b", None),
                getattr(cls, "_token_dir_b", None),
            )
        if hasattr(cls, "_jobs_directory"):
            shutil.rmtree(cls._jobs_directory, ignore_errors=True)

    def setUp(self) -> None:
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        job_conf_str = _two_cluster_job_conf(
            cls._collector_addr,
            cls._host_config_path,
            cls._collector_addr_b,
            cls._host_config_path_b,
        )
        with tempfile.NamedTemporaryFile(suffix="_htcondor_container_job_conf.yml", mode="w", delete=False) as f:
            f.write(job_conf_str)
        config["job_config_file"] = f.name
        config["job_working_directory"] = cls._jobs_directory
        config["file_path"] = os.path.join(cls._jobs_directory, "files")
        config["new_file_path"] = os.path.join(cls._jobs_directory, "new_files")

    @skip_without_tool("simple_constructs")
    def test_htcondor_docker_job(self) -> None:
        """A job submitted to cluster A via htcondor/mini finishes successfully."""
        before_a = _condor_history_count(self._container_name)
        before_b = _condor_history_count(self._container_name_b)
        self._run_tool_test("simple_constructs", maxseconds=300)
        assert _condor_history_count(self._container_name) > before_a, "No new completed job in cluster A"
        assert _condor_history_count(self._container_name_b) == before_b, "Unexpected job appeared in cluster B"

    @skip_without_tool("cat_data_and_sleep")
    def test_htcondor_docker_cancel(self) -> None:
        """Cancelling a running job calls condor_rm and the job reaches DELETED."""
        with self.dataset_populator.test_history() as history_id:
            hda = self.dataset_populator.new_dataset(history_id, content="1 2 3")
            run_response = self.dataset_populator.run_tool(
                "cat_data_and_sleep",
                {"input1": {"src": "hda", "id": hda["id"]}, "sleep_time": 300},
                history_id,
            )
            job_id = run_response["jobs"][0]["id"]

            app = self._app
            sa_session = app.model.session
            job = sa_session.get(model.Job, app.security.decode_id(job_id))
            assert job

            # Wait for the job to be submitted to the real schedd.
            for _ in range(60):
                sa_session.refresh(job)
                if job.job_runner_external_id:
                    break
                time.sleep(1)
            assert job.job_runner_external_id, "Job was never submitted to the HTCondor schedd"

            # Cancel via the Galaxy API.
            delete_response = self.dataset_populator.cancel_job(job_id)
            assert delete_response.json() is True

            # Wait for the Galaxy job record to reach the terminal DELETED state.
            for _ in range(60):
                sa_session.refresh(job)
                if job.state == model.Job.states.DELETED:
                    break
                time.sleep(1)
            assert job.state == model.Job.states.DELETED, f"Expected DELETED, got {job.state}"

    @skip_without_tool("checksum")
    def test_htcondor_docker_job_cluster_b(self) -> None:
        """A job routed to cluster B finishes successfully and does not appear in cluster A."""
        before_a = _condor_history_count(self._container_name)
        before_b = _condor_history_count(self._container_name_b)
        self._run_tool_test("checksum", maxseconds=300)
        assert _condor_history_count(self._container_name) == before_a, "Unexpected job appeared in cluster A"
        assert _condor_history_count(self._container_name_b) > before_b, "No new completed job in cluster B"

    @skip_without_tool("cat_data_and_sleep")
    def test_htcondor_docker_job_killed_externally(self) -> None:
        """A job removed via condor_rm inside the container is failed in Galaxy.

        Simulates an admin running condor_rm, a node eviction, or any other
        external termination that is not initiated by Galaxy.  The runner must
        detect the JOB_ABORTED event and transition the Galaxy job to ERROR.
        """
        with self.dataset_populator.test_history() as history_id:
            hda = self.dataset_populator.new_dataset(history_id, content="1 2 3")
            run_response = self.dataset_populator.run_tool(
                "cat_data_and_sleep",
                {"input1": {"src": "hda", "id": hda["id"]}, "sleep_time": 300},
                history_id,
            )
            job_id = run_response["jobs"][0]["id"]

            app = self._app
            sa_session = app.model.session
            job = sa_session.get(model.Job, app.security.decode_id(job_id))
            assert job

            for _ in range(60):
                sa_session.refresh(job)
                if job.job_runner_external_id:
                    break
                time.sleep(1)
            assert job.job_runner_external_id, "Job was never submitted to the HTCondor schedd"

            subprocess.run(
                ["docker", "exec", self._container_name, "condor_rm", job.job_runner_external_id],
                check=True,
            )

            for _ in range(60):
                sa_session.refresh(job)
                if job.state in (model.Job.states.ERROR, model.Job.states.DELETED):
                    break
                time.sleep(1)
            assert job.state == model.Job.states.ERROR, f"Expected ERROR after external condor_rm, got {job.state}"


class FakeHTCondorIntegrationInstance(integration_util.IntegrationInstance):
    """Galaxy app instance backed by the fake htcondor2 module.

    Used by unit-style tests that exercise the runner directly without going
    through Galaxy's job routing system.
    """

    framework_tool_and_types = True
    _fake_record_dir: str
    _old_pythonpath: str | None
    _added_fake_sys_path: bool

    @classmethod
    def _prepare_galaxy(cls):
        sys.modules.pop("htcondor2", None)
        cls._fake_record_dir = tempfile.mkdtemp(prefix="fake_htcondor_records_")
        cls._old_pythonpath = os.environ.get("PYTHONPATH")
        cls._added_fake_sys_path = LIVE_FAKE_MODULE_PATH not in sys.path
        if cls._added_fake_sys_path:
            sys.path.insert(0, LIVE_FAKE_MODULE_PATH)
        fake_pythonpath = LIVE_FAKE_MODULE_PATH
        if cls._old_pythonpath:
            os.environ["PYTHONPATH"] = f"{fake_pythonpath}{os.pathsep}{cls._old_pythonpath}"
        else:
            os.environ["PYTHONPATH"] = fake_pythonpath
        os.environ["GALAXY_TEST_FAKE_HTCONDOR_RECORD_DIR"] = cls._fake_record_dir

    @classmethod
    def tearDownClass(cls):
        try:
            super().tearDownClass()
        finally:
            sys.modules.pop("htcondor2", None)
            if cls._added_fake_sys_path and LIVE_FAKE_MODULE_PATH in sys.path:
                sys.path.remove(LIVE_FAKE_MODULE_PATH)
            if cls._old_pythonpath is None:
                os.environ.pop("PYTHONPATH", None)
            else:
                os.environ["PYTHONPATH"] = cls._old_pythonpath
            os.environ.pop("GALAXY_TEST_FAKE_HTCONDOR_RECORD_DIR", None)
            shutil.rmtree(cls._fake_record_dir, ignore_errors=True)


fake_instance = integration_util.integration_module_instance(FakeHTCondorIntegrationInstance)


class FakeHTCondorJobIntegrationInstance(FakeHTCondorIntegrationInstance):
    """Like FakeHTCondorIntegrationInstance but configures Galaxy's job routing
    to use the htcondor runner end-to-end, with auto-completion so submitted
    jobs finish without a real HTCondor installation.
    """

    @classmethod
    def _prepare_galaxy(cls):
        super()._prepare_galaxy()
        os.environ["GALAXY_TEST_FAKE_HTCONDOR_AUTO_COMPLETE"] = "1"

    @classmethod
    def tearDownClass(cls):
        try:
            super().tearDownClass()
        finally:
            os.environ.pop("GALAXY_TEST_FAKE_HTCONDOR_AUTO_COMPLETE", None)

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        job_conf_str = _fake_job_conf()
        with tempfile.NamedTemporaryFile(suffix="_fake_htcondor_job_conf.yml", mode="w", delete=False) as job_conf:
            job_conf.write(job_conf_str)
        config["job_config_file"] = job_conf.name


fake_job_instance = integration_util.integration_module_instance(FakeHTCondorJobIntegrationInstance)


def test_fake_end_to_end_job(fake_job_instance):
    """Full Galaxy job lifecycle via the htcondor runner backed by the fake module."""
    fake_job_instance._run_tool_test("simple_constructs")


class FakeHTCondorCancelIntegrationInstance(FakeHTCondorIntegrationInstance):
    """Like FakeHTCondorJobIntegrationInstance but without auto-completion.

    Jobs are submitted to the fake schedd and stay pending indefinitely, which
    allows the test to cancel them via the Galaxy API before they finish.
    AUTO_COMPLETE is explicitly cleared so this instance is not affected by
    other module-scoped fixtures that enable it.
    """

    @classmethod
    def _prepare_galaxy(cls):
        super()._prepare_galaxy()
        # Clear auto-complete so jobs stay pending and can be cancelled.
        os.environ.pop("GALAXY_TEST_FAKE_HTCONDOR_AUTO_COMPLETE", None)

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        job_conf_str = _fake_job_conf()
        with tempfile.NamedTemporaryFile(suffix="_fake_htcondor_cancel_job_conf.yml", mode="w", delete=False) as f:
            f.write(job_conf_str)
        config["job_config_file"] = f.name


fake_cancel_instance = integration_util.integration_module_instance(FakeHTCondorCancelIntegrationInstance)


def test_fake_cancel_job(fake_cancel_instance):
    """Cancel a pending htcondor job via the Galaxy API and verify condor_rm is called."""
    fake_cancel_instance.dataset_populator = DatasetPopulator(fake_cancel_instance.galaxy_interactor)
    with fake_cancel_instance.dataset_populator.test_history() as history_id:
        hda = fake_cancel_instance.dataset_populator.new_dataset(history_id, content="1 2 3")
        run_response = fake_cancel_instance.dataset_populator.run_tool(
            "cat_data_and_sleep",
            {"input1": {"src": "hda", "id": hda["id"]}, "sleep_time": 300},
            history_id,
        )
        job_id = run_response["jobs"][0]["id"]

        app = fake_cancel_instance._app
        sa_session = app.model.session
        job = sa_session.get(model.Job, app.security.decode_id(job_id))
        assert job

        # Wait for the job to be submitted to the fake schedd (external_id set).
        for _ in range(60):
            sa_session.refresh(job)
            if job.job_runner_external_id:
                break
            time.sleep(1)
        assert job.job_runner_external_id, "Job was never submitted to the fake htcondor schedd"
        external_id = job.job_runner_external_id

        # Cancel via Galaxy API.
        delete_response = fake_cancel_instance.dataset_populator.cancel_job(job_id)
        assert delete_response.json() is True

        # Wait for the job to reach the DELETED terminal state.
        for _ in range(30):
            sa_session.refresh(job)
            if job.state == model.Job.states.DELETED:
                break
            time.sleep(1)
        assert job.state == model.Job.states.DELETED, f"Expected DELETED, got {job.state}"

        # Verify the fake schedd received a Remove action for this job.
        remove_records = _records(fake_cancel_instance, kind="remove")
        assert remove_records, "No condor remove record written — stop_job was not called"
        assert int(remove_records[0]["job_spec"]) == int(external_id)


class FastFakeHTCondorJobRunner(htcondor.HTCondorJobRunner):
    def prepare_job(
        self,
        job_wrapper,
        include_metadata=False,
        include_work_dir_outputs=True,
        modify_command_for_container=True,
        stream_stdout_stderr=False,
    ):
        job_state = job_wrapper.get_state()
        if job_state == model.Job.states.DELETED:
            return False
        if job_state not in (model.Job.states.QUEUED, model.Job.states.NEW):
            return False
        job_wrapper.prepare()
        job_wrapper.runner_command_line = job_wrapper.command_line
        return True

    def get_job_file(self, job_wrapper, **kwds):
        return "#!/bin/bash\nexit 0\n"

    def write_executable_script(self, path, contents, job_io):
        with open(path, "w") as handle:
            handle.write(contents)
        os.chmod(path, 0o755)


@pytest.fixture
def fake_htcondor(fake_instance):
    record_dir = fake_instance._fake_record_dir
    module = importlib.import_module("htcondor2")
    for entry in os.listdir(record_dir):
        os.unlink(os.path.join(record_dir, entry))
    module.JobEventLog.events_by_log.clear()
    yield module
    module.JobEventLog.events_by_log.clear()
    for entry in os.listdir(record_dir):
        os.unlink(os.path.join(record_dir, entry))


@pytest.fixture
def runner_factory(fake_instance):
    runners = []
    original_helper_module = htcondor.HTCONDOR_HELPER_MODULE

    def create_runner():
        runner = FastFakeHTCondorJobRunner(fake_instance._app, 1)
        runner.work_queue = Queue()
        runners.append(runner)
        return runner

    htcondor.HTCONDOR_HELPER_MODULE = "htcondor_helper"
    yield create_runner
    htcondor.HTCONDOR_HELPER_MODULE = original_helper_module

    for runner in runners:
        work_threads = getattr(runner, "work_threads", None)
        if work_threads is not None and not runner._should_stop:
            runner.shutdown()
        else:
            runner._shutdown_clients()


def _tool(fake_instance):
    tool = fake_instance._app.toolbox.get_tool("create_2")
    assert tool is not None
    return tool


def _job_wrapper(fake_instance, job_id, destination_params=None, *, state=model.Job.states.QUEUED):
    return MockJobWrapper(
        fake_instance._app,
        fake_instance._tempdir,
        _tool(fake_instance),
        destination_params or {},
        job_id,
        state=state,
    )


def _records(fake_instance, kind=None):
    records = []
    for entry in sorted(os.listdir(fake_instance._fake_record_dir)):
        path = os.path.join(fake_instance._fake_record_dir, entry)
        with open(path) as handle:
            record = json.load(handle)
        if kind is None or record["kind"] == kind:
            records.append(record)
    return records


def _watch_job(runner, job_wrapper, external_id="123"):
    cjs = htcondor.HTCondorJobState(
        job_wrapper=job_wrapper,
        job_destination=job_wrapper.job_destination,
        user_log=os.path.join(
            job_wrapper.working_directory,
            f"galaxy_{job_wrapper.get_id_tag()}.condor.log",
        ),
        files_dir=job_wrapper.working_directory,
        job_id=external_id,
    )
    cjs.register_cleanup_file_attribute("user_log")
    runner.watched = [cjs]
    return cjs


def _write_user_log(cjs):
    with open(cjs.user_log, "w") as handle:
        handle.write("1")


def _set_job_events(fake_htcondor, cjs, event_names):
    fake_htcondor.JobEventLog.set_events(
        cjs.user_log,
        [
            fake_htcondor.FakeJobEvent(int(cjs.job_id), 0, getattr(fake_htcondor.JobEventType, event_name))
            for event_name in event_names
        ],
    )


@pytest.mark.parametrize(
    (
        "destination_params",
        "event_names",
        "job_state",
        "create_log",
        "expected_method_name",
        "expected_wrapper_state",
        "expected_running",
        "expected_watched_count",
        "expect_entry_points",
    ),
    [
        pytest.param(
            dict(htcondor_config="/tmp/condor-execute"),
            ["EXECUTE"],
            None,
            True,
            None,
            model.Job.states.RUNNING,
            True,
            1,
            True,
            id="execute-sets-running",
        ),
        pytest.param(
            dict(htcondor_config="/tmp/condor-terminated"),
            ["JOB_TERMINATED"],
            None,
            True,
            "finish_job",
            model.Job.states.QUEUED,
            False,
            0,
            False,
            id="terminated-finishes",
        ),
        pytest.param(
            dict(htcondor_config="/tmp/condor-aborted"),
            ["JOB_ABORTED"],
            None,
            True,
            "fail_job",
            model.Job.states.QUEUED,
            False,
            0,
            False,
            id="aborted-fails",
        ),
        pytest.param(
            dict(htcondor_config="/tmp/condor-removed"),
            ["CLUSTER_REMOVE"],
            None,
            True,
            "fail_job",
            model.Job.states.QUEUED,
            False,
            0,
            False,
            id="cluster-remove-fails",
        ),
        pytest.param(
            dict(htcondor_config="/tmp/condor-shadow"),
            ["SHADOW_EXCEPTION"],
            None,
            True,
            "fail_job",
            model.Job.states.QUEUED,
            False,
            0,
            False,
            id="shadow-exception-fails",
        ),
        pytest.param(
            dict(htcondor_config="/tmp/condor-exe-error"),
            ["EXECUTABLE_ERROR"],
            None,
            True,
            "fail_job",
            model.Job.states.QUEUED,
            False,
            0,
            False,
            id="executable-error-fails",
        ),
        pytest.param(
            dict(htcondor_config="/tmp/condor-held-stays"),
            ["JOB_HELD"],
            None,
            True,
            None,
            model.Job.states.QUEUED,
            False,
            1,
            False,
            id="held-stays-watched",
        ),
        pytest.param(
            dict(htcondor_config="/tmp/condor-held-stopped"),
            ["JOB_HELD"],
            model.Job.states.STOPPED,
            True,
            "finish_job",
            model.Job.states.STOPPED,
            False,
            0,
            False,
            id="held-stopped-finishes",
        ),
        pytest.param(
            dict(htcondor_config="/tmp/condor-held-failed"),
            ["JOB_HELD", "JOB_ABORTED"],
            None,
            True,
            "fail_job",
            model.Job.states.QUEUED,
            False,
            0,
            False,
            id="held-terminal-fails",
        ),
        pytest.param(
            dict(htcondor_config="/tmp/condor-released"),
            ["JOB_HELD", "JOB_RELEASED"],
            None,
            True,
            None,
            model.Job.states.QUEUED,
            False,
            1,
            False,
            id="held-released-stays-watched",
        ),
        pytest.param(
            dict(htcondor_config="/tmp/condor-suspended"),
            ["EXECUTE", "JOB_SUSPENDED"],
            None,
            True,
            None,
            model.Job.states.QUEUED,
            False,
            1,
            False,
            id="suspended-stops-running",
        ),
        pytest.param(
            dict(htcondor_config="/tmp/condor-unsuspended"),
            ["EXECUTE", "JOB_SUSPENDED", "JOB_UNSUSPENDED"],
            None,
            True,
            None,
            model.Job.states.RUNNING,
            True,
            1,
            True,
            id="unsuspended-resumes-running",
        ),
        pytest.param(
            dict(htcondor_config="/tmp/condor-missing-log"),
            [],
            None,
            False,
            None,
            model.Job.states.QUEUED,
            False,
            1,
            False,
            id="missing-log-stays-watched",
        ),
        pytest.param(
            dict(htcondor_config="/tmp/condor-aborted-user-deleted"),
            ["JOB_ABORTED"],
            model.Job.states.DELETED,
            True,
            None,
            model.Job.states.DELETED,
            False,
            0,
            False,
            id="aborted-after-user-delete-is-ignored",
        ),
        pytest.param(
            dict(htcondor_config="/tmp/condor-aborted-user-stopped"),
            ["JOB_ABORTED"],
            model.Job.states.STOPPED,
            True,
            "finish_job",
            model.Job.states.STOPPED,
            False,
            0,
            False,
            id="aborted-after-user-stop-finishes",
        ),
    ],
)
def test_watch_lifecycle_transitions(
    fake_instance,
    fake_htcondor,
    runner_factory,
    destination_params,
    event_names,
    job_state,
    create_log,
    expected_method_name,
    expected_wrapper_state,
    expected_running,
    expected_watched_count,
    expect_entry_points,
):
    runner = runner_factory()
    job_wrapper = _job_wrapper(fake_instance, 1, destination_params)
    cjs = _watch_job(runner, job_wrapper)

    if create_log:
        _write_user_log(cjs)
    if event_names:
        _set_job_events(fake_htcondor, cjs, event_names)
    if job_state is not None:
        job_wrapper.state = job_state

    runner.check_watched_items()

    if expected_method_name is None:
        assert runner.work_queue.empty()
    else:
        method, job_state_record = runner.work_queue.get_nowait()
        assert method == getattr(runner, expected_method_name)
        assert job_state_record.job_id == cjs.job_id
        assert runner.work_queue.empty()

    assert len(runner.watched) == expected_watched_count
    if expected_watched_count:
        assert runner.watched[0] is cjs
        assert runner.watched[0].running is expected_running
    assert job_wrapper.state == expected_wrapper_state
    assert job_wrapper.entry_points_checked is expect_entry_points


def test_held_released_then_executes_and_finishes(fake_instance, fake_htcondor, runner_factory):
    """A job that is held, released, then executes and terminates completes normally."""
    runner = runner_factory()
    job_wrapper = _job_wrapper(fake_instance, 1, dict(htcondor_config="/tmp/condor-held-released-finish"))
    cjs = _watch_job(runner, job_wrapper)
    _write_user_log(cjs)

    # Cycle 1: job is held then released — should stay watched, not running
    _set_job_events(fake_htcondor, cjs, ["JOB_HELD", "JOB_RELEASED"])
    runner.check_watched_items()
    assert runner.work_queue.empty()
    assert len(runner.watched) == 1
    assert not runner.watched[0].running

    # Cycle 2: job re-executes and terminates
    _set_job_events(fake_htcondor, cjs, ["EXECUTE", "JOB_TERMINATED"])
    runner.check_watched_items()
    method, job_state_record = runner.work_queue.get_nowait()
    assert method == runner.finish_job
    assert job_state_record.job_id == cjs.job_id
    assert runner.watched == []


def test_different_configs_use_separate_helpers(fake_instance, fake_htcondor, runner_factory):
    runner = runner_factory()
    runner.queue_job(
        _job_wrapper(
            fake_instance,
            1,
            dict(htcondor_config="/tmp/condor-A", htcondor_schedd="schedd@alpha"),
        )
    )
    runner.queue_job(
        _job_wrapper(
            fake_instance,
            2,
            dict(htcondor_config="/tmp/condor-B", htcondor_schedd="schedd@beta"),
        )
    )

    records = _records(fake_instance, "submit")
    assert len(records) == 2
    assert {record["config"] for record in records} == {
        os.path.realpath("/tmp/condor-A"),
        os.path.realpath("/tmp/condor-B"),
    }
    assert {record["schedd_name"] for record in records} == {
        "schedd@alpha",
        "schedd@beta",
    }
    assert len({record["pid"] for record in records}) == 2


def test_same_config_reuses_helper_across_shedds(fake_instance, fake_htcondor, runner_factory):
    runner = runner_factory()
    shared_config = "/tmp/condor-shared"
    runner.queue_job(
        _job_wrapper(
            fake_instance,
            1,
            dict(
                htcondor_config=shared_config,
                htcondor_collector="collector:9618",
                htcondor_schedd="schedd@alpha",
            ),
        )
    )
    runner.queue_job(
        _job_wrapper(
            fake_instance,
            2,
            dict(
                htcondor_config=shared_config,
                htcondor_collector="collector:9618",
                htcondor_schedd="schedd@beta",
            ),
        )
    )

    records = _records(fake_instance, "submit")
    assert len(records) == 2
    assert {record["config"] for record in records} == {os.path.realpath(shared_config)}
    assert {record["schedd_name"] for record in records} == {
        "schedd@alpha",
        "schedd@beta",
    }
    assert {record["collector"] for record in records} == {"collector:9618"}
    assert len({record["pid"] for record in records}) == 1
    for record in records:
        assert "htcondor_config" not in record["submit_description"]
        assert "htcondor_collector" not in record["submit_description"]
        assert "htcondor_schedd" not in record["submit_description"]


def test_stop_job_uses_same_config_scoped_helper(fake_instance, fake_htcondor, runner_factory):
    runner = runner_factory()
    job_wrapper = _job_wrapper(
        fake_instance,
        1,
        dict(htcondor_config="/tmp/condor-stop", htcondor_schedd="schedd@stop"),
    )
    runner.queue_job(job_wrapper)
    runner.stop_job(job_wrapper)

    submit_record = _records(fake_instance, "submit")[0]
    remove_record = _records(fake_instance, "remove")[0]
    assert submit_record["pid"] == remove_record["pid"]
    assert submit_record["config"] == remove_record["config"] == os.path.realpath("/tmp/condor-stop")
    assert remove_record["schedd_name"] == "schedd@stop"
    assert remove_record["job_spec"] == int(job_wrapper.job.job_runner_external_id)


@pytest.mark.parametrize(
    "state",
    [model.Job.states.STOPPED, model.Job.states.DELETED],
    ids=["stopped", "deleted"],
)
def test_stopped_or_deleted_jobs_are_not_submitted(fake_instance, fake_htcondor, runner_factory, state):
    runner = runner_factory()
    job_wrapper = _job_wrapper(
        fake_instance,
        1,
        dict(htcondor_config="/tmp/condor-cancelled"),
        state=state,
    )

    runner.queue_job(job_wrapper)

    assert _records(fake_instance) == []
    assert runner.monitor_queue.empty()
    assert runner._client_cache == {}


@pytest.mark.parametrize(
    "job_state, expected_running",
    [
        pytest.param(model.Job.states.QUEUED, False, id="queued"),
        pytest.param(model.Job.states.RUNNING, True, id="running"),
        pytest.param(model.Job.states.STOPPED, True, id="stopped"),
    ],
)
def test_recover_readds_monitored_jobs(fake_instance, fake_htcondor, runner_factory, job_state, expected_running):
    runner = runner_factory()
    job = model.Job()
    job.id = 7
    job.state = job_state
    job.job_runner_external_id = "123"
    job_wrapper = _job_wrapper(fake_instance, 7, dict(htcondor_config="/tmp/condor-recover"))

    runner.recover(job, job_wrapper)

    cjs = runner.monitor_queue.get_nowait()
    assert cjs.job_id == "123"
    assert cjs.running is expected_running
    assert cjs.job_wrapper is job_wrapper


def test_recover_without_external_id_requeues_job(fake_instance, fake_htcondor, runner_factory, monkeypatch):
    runner = runner_factory()
    job = model.Job()
    job.id = 8
    job.state = model.Job.states.QUEUED
    job_wrapper = _job_wrapper(fake_instance, 8, dict(htcondor_config="/tmp/condor-requeue"))
    put_calls = []
    monkeypatch.setattr(
        runner,
        "put",
        lambda recovered_job_wrapper: put_calls.append(recovered_job_wrapper),
    )

    runner.recover(job, job_wrapper)

    assert put_calls == [job_wrapper]
    assert runner.monitor_queue.empty()


def test_runner_shutdown_terminates_all_helpers(fake_instance, fake_htcondor, runner_factory):
    runner = runner_factory()
    runner.work_threads = []
    runner.shutdown_monitor = lambda: None
    runner.queue_job(
        _job_wrapper(
            fake_instance,
            1,
            dict(htcondor_config="/tmp/condor-A", htcondor_schedd="schedd@alpha"),
        )
    )
    runner.queue_job(
        _job_wrapper(
            fake_instance,
            2,
            dict(htcondor_config="/tmp/condor-B", htcondor_schedd="schedd@beta"),
        )
    )

    clients = list(runner._client_cache.values())
    processes = [client._process for client in clients if getattr(client, "_process", None) is not None]
    assert len(processes) == 2
    assert all(process.poll() is None for process in processes)

    runner.shutdown()

    assert all(getattr(client, "_process", None) is None for client in clients)
    assert all(process.poll() is not None for process in processes)


def test_helper_respawns_after_crash(fake_instance, fake_htcondor, runner_factory):
    runner = runner_factory()
    destination_params = dict(htcondor_config="/tmp/condor-respawn", htcondor_schedd="schedd@respawn")
    first_job_wrapper = _job_wrapper(fake_instance, 1, destination_params)
    second_job_wrapper = _job_wrapper(fake_instance, 2, destination_params)
    runner.queue_job(first_job_wrapper)

    client = runner._client_for_destination(first_job_wrapper.job_destination)
    process = client._process
    assert process is not None
    first_pid = process.pid
    process.kill()
    process.wait(timeout=5)

    runner.queue_job(second_job_wrapper)

    submit_records = _records(fake_instance, "submit")
    assert len(submit_records) == 2
    assert submit_records[0]["pid"] == first_pid
    assert submit_records[1]["pid"] != first_pid
    assert submit_records[1]["config"] == os.path.realpath(destination_params["htcondor_config"])


def test_finish_handles_external_metadata(fake_instance, fake_htcondor, runner_factory, monkeypatch):
    runner = runner_factory()
    job_wrapper = _job_wrapper(
        fake_instance,
        1,
        dict(htcondor_config="/tmp/condor-external-metadata", embed_metadata_in_job=False),
    )
    cjs = _watch_job(runner, job_wrapper)
    _write_user_log(cjs)
    _set_job_events(fake_htcondor, cjs, ["JOB_TERMINATED"])
    metadata_calls = []

    def handle_metadata_externally(job_wrapper_arg, resolve_requirements=False):
        metadata_calls.append((job_wrapper_arg, resolve_requirements))

    monkeypatch.setattr(runner, "_handle_metadata_externally", handle_metadata_externally)

    runner.check_watched_items()

    method, job_state_record = runner.work_queue.get_nowait()
    assert method == runner.finish_job
    assert job_state_record.job_id == cjs.job_id
    assert metadata_calls == [(job_wrapper, True)]
    assert runner.watched == []


def test_submit_failure_fails_job(fake_instance, fake_htcondor, runner_factory, monkeypatch):
    runner = runner_factory()
    job_wrapper = _job_wrapper(fake_instance, 1, dict(htcondor_config="/tmp/condor-submit-fail"))

    def failing_submit(*args, **kwargs):
        raise RuntimeError("schedd unavailable")

    client = runner._client_for_destination(job_wrapper.job_destination)
    monkeypatch.setattr(client, "submit", failing_submit)

    runner.queue_job(job_wrapper)

    assert hasattr(job_wrapper, "fail_message")
    assert "htcondor submit failed" in job_wrapper.fail_message
    assert runner.monitor_queue.empty()


def test_condor_remove_failure_is_logged(fake_instance, fake_htcondor, runner_factory, monkeypatch):
    runner = runner_factory()
    job_wrapper = _job_wrapper(fake_instance, 1, dict(htcondor_config="/tmp/condor-remove-fail"))
    runner.queue_job(job_wrapper)

    client = runner._client_for_destination(job_wrapper.job_destination)

    def failing_remove(*args, **kwargs):
        raise RuntimeError("condor_rm failed")

    monkeypatch.setattr(client, "remove", failing_remove)

    failure_msg = runner._condor_remove(job_wrapper.job.job_runner_external_id, job_wrapper.job_destination)
    assert failure_msg is not None
    assert "condor_rm failed" in failure_msg


@pytest.mark.parametrize(
    ("event_name", "config_tag"),
    [
        pytest.param("JOB_TERMINATED", "close-log-complete", id="complete"),
        pytest.param("JOB_ABORTED", "close-log-fail", id="fail"),
    ],
)
def test_event_log_closed_on_terminal_event(fake_instance, fake_htcondor, runner_factory, event_name, config_tag):
    """Event log is closed and its reference cleared after any terminal event."""
    runner = runner_factory()
    job_wrapper = _job_wrapper(fake_instance, 1, dict(htcondor_config=f"/tmp/condor-{config_tag}"))
    cjs = _watch_job(runner, job_wrapper)
    _write_user_log(cjs)
    _set_job_events(fake_htcondor, cjs, [event_name])

    _ = cjs.event_log(runner.htcondor)
    assert cjs._event_log is not None

    runner.check_watched_items()

    assert cjs._event_log is None


@pytest.mark.parametrize(
    ("event_name", "expected_message_fragment", "expect_unknown_error_runner_state"),
    [
        ("SHADOW_EXCEPTION", "shadow exception", True),
        ("JOB_ABORTED", "removed from the HTCondor queue", True),
        ("CLUSTER_REMOVE", "cluster was removed", True),
        ("EXECUTABLE_ERROR", "could not start", False),
    ],
)
def test_failure_event_sets_message_and_runner_state(
    fake_instance,
    fake_htcondor,
    runner_factory,
    event_name,
    expected_message_fragment,
    expect_unknown_error_runner_state,
):
    """Each failure event type sets a distinct fail_message and the correct runner_state."""
    from galaxy.jobs.runners.util import runner_states as rs

    runner = runner_factory()
    job_wrapper = _job_wrapper(fake_instance, 1, dict(htcondor_config=f"/tmp/condor-msg-{event_name}"))
    cjs = _watch_job(runner, job_wrapper)
    _write_user_log(cjs)
    _set_job_events(fake_htcondor, cjs, [event_name])

    runner.check_watched_items()

    method, job_state_record = runner.work_queue.get_nowait()
    assert method == runner.fail_job
    assert expected_message_fragment.lower() in job_state_record.fail_message.lower()
    if expect_unknown_error_runner_state:
        assert job_state_record.runner_state == rs.UNKNOWN_ERROR
    else:
        assert getattr(job_state_record, "runner_state", None) is None


def test_events_across_two_cycles(fake_instance, fake_htcondor, runner_factory):
    """Events arriving in separate monitor cycles carry cjs.running correctly."""
    runner = runner_factory()
    job_wrapper = _job_wrapper(fake_instance, 1, dict(htcondor_config="/tmp/condor-two-cycles"))
    cjs = _watch_job(runner, job_wrapper)
    _write_user_log(cjs)

    # Cycle 1: job starts executing.
    _set_job_events(fake_htcondor, cjs, ["EXECUTE"])
    runner.check_watched_items()
    assert len(runner.watched) == 1
    assert runner.watched[0].running is True
    assert runner.work_queue.empty()
    assert job_wrapper.state == model.Job.states.RUNNING

    # Cycle 2: job terminates — cjs.running must be True coming in so that
    # the state transition is handled correctly.
    _set_job_events(fake_htcondor, cjs, ["JOB_TERMINATED"])
    runner.check_watched_items()
    assert len(runner.watched) == 0
    method, _ = runner.work_queue.get_nowait()
    assert method == runner.finish_job


def test_recover_with_completed_event_log(fake_instance, fake_htcondor, runner_factory):
    """recover() re-queues a RUNNING job; finish_job is called on the next cycle
    if the event log already shows the job completed while Galaxy was down."""
    runner = runner_factory()
    job = model.Job()
    job.id = 99
    job.state = model.Job.states.RUNNING
    job.job_runner_external_id = "456"
    job_wrapper = _job_wrapper(
        fake_instance, 99, dict(htcondor_config="/tmp/condor-recover-done"), state=model.Job.states.RUNNING
    )

    runner.recover(job, job_wrapper)

    # Simulate what the monitor thread does: drain monitor_queue into watched.
    cjs = runner.monitor_queue.get_nowait()
    runner.watched = [cjs]

    # Pre-populate the event log with the full lifecycle including completion.
    _write_user_log(cjs)
    _set_job_events(fake_htcondor, cjs, ["EXECUTE", "JOB_TERMINATED"])

    runner.check_watched_items()

    assert len(runner.watched) == 0
    method, _ = runner.work_queue.get_nowait()
    assert method == runner.finish_job


def test_transient_status_error_retries_before_failing(fake_instance, fake_htcondor, runner_factory, monkeypatch):
    """Transient errors from _summarize_event_log keep the job watched for
    MAX_STATUS_ERROR_COUNT-1 cycles, then fail it on the final error."""
    from galaxy.jobs.runners import htcondor as htcondor_module

    runner = runner_factory()
    job_wrapper = _job_wrapper(fake_instance, 1, dict(htcondor_config="/tmp/condor-transient-err"))
    cjs = _watch_job(runner, job_wrapper)
    _write_user_log(cjs)

    call_count = 0

    def always_raise(c):
        nonlocal call_count
        call_count += 1
        raise OSError("simulated NFS timeout")

    monkeypatch.setattr(runner, "_summarize_event_log", always_raise)

    max_count = htcondor_module.MAX_STATUS_ERROR_COUNT

    # First MAX_STATUS_ERROR_COUNT-1 errors: job stays in watched, nothing queued.
    for i in range(max_count - 1):
        runner.check_watched_items()
        assert len(runner.watched) == 1, f"job should still be watched after error {i + 1}"
        assert runner.work_queue.empty(), f"no failure should be queued after error {i + 1}"
        assert cjs.status_error_count == i + 1

    # Final error: job is failed.
    runner.check_watched_items()
    assert len(runner.watched) == 0
    method, job_state_record = runner.work_queue.get_nowait()
    assert method == runner.fail_job
    assert job_state_record.status_error_count == max_count


def test_held_job_escalates_to_failure_after_max_count(fake_instance, fake_htcondor, runner_factory):
    """A job that is held max_held_count times without release is permanently failed."""
    runner = runner_factory()
    job_wrapper = _job_wrapper(fake_instance, 1, dict(htcondor_config="/tmp/condor-held-escalate"))
    cjs = _watch_job(runner, job_wrapper)
    _write_user_log(cjs)

    max_held = int(job_wrapper.job_destination.params.get("max_held_count", 3))

    # Each cycle delivers a new JOB_HELD event and keeps the job in watched
    # until the threshold is reached.
    for i in range(max_held - 1):
        _set_job_events(fake_htcondor, cjs, ["JOB_HELD"])
        runner.check_watched_items()
        assert len(runner.watched) == 1, f"job should still be watched after hold {i + 1}"
        assert runner.work_queue.empty()
        assert cjs.held_count == i + 1

    # Final hold: threshold reached, job is failed.
    _set_job_events(fake_htcondor, cjs, ["JOB_HELD"])
    runner.check_watched_items()
    assert len(runner.watched) == 0
    method, job_state_record = runner.work_queue.get_nowait()
    assert method == runner.fail_job
    assert job_state_record.held_count == max_held
    assert "held" in job_state_record.fail_message.lower()


def test_held_job_max_count_is_configurable(fake_instance, fake_htcondor, runner_factory):
    """max_held_count destination param overrides the default escalation threshold."""
    runner = runner_factory()
    job_wrapper = _job_wrapper(fake_instance, 1, dict(htcondor_config="/tmp/condor-held-custom", max_held_count="1"))
    cjs = _watch_job(runner, job_wrapper)
    _write_user_log(cjs)

    # With max_held_count=1 the very first hold should fail the job.
    _set_job_events(fake_htcondor, cjs, ["JOB_HELD"])
    runner.check_watched_items()

    assert len(runner.watched) == 0
    method, _ = runner.work_queue.get_nowait()
    assert method == runner.fail_job


class MockJobWrapper:
    def __init__(
        self,
        app,
        test_directory,
        tool,
        destination_params,
        job_id,
        state=model.Job.states.QUEUED,
    ):
        working_directory = tempfile.mkdtemp(prefix="htcondor_workdir_", dir=test_directory)
        tool_working_directory = os.path.join(working_directory, "working")
        os.makedirs(tool_working_directory)
        self.app = app
        self.tool = tool
        self.requires_containerization = False
        self.state = state
        self.command_line = "echo HelloWorld"
        self.environment_variables = []
        self.commands_in_new_shell = False
        self.prepare_called = False
        self.dependency_shell_commands = None
        self.working_directory = working_directory
        self.tool_working_directory = tool_working_directory
        self.requires_setting_metadata = True
        self.job_destination = JobDestination(id=f"htcondor_destination_{job_id}", params=destination_params)
        self.galaxy_lib_dir = os.path.abspath("lib")
        self.job = model.Job()
        self.job_id = job_id
        self.job.id = job_id
        self.job.container = None
        self.output_paths = ["/tmp/output1.dat"]
        self.mock_metadata_path = os.path.join(working_directory, f"METADATA_SET_{job_id}")
        self.metadata_command = f"touch {self.mock_metadata_path}"
        self.galaxy_virtual_env = None
        self.shell = "/bin/bash"
        self.cleanup_job = "never"
        self.tmp_dir_creation_statement = ""
        self.use_metadata_binary = False
        self.guest_ports = []
        self.metadata_strategy = "directory"
        self.remote_command_line = False
        self.entry_points_checked = False
        self.cleanup_called = False
        self.user = None

        self.external_output_metadata = bunch.Bunch()
        self.app.datatypes_registry.set_external_metadata_tool = bunch.Bunch(build_dependency_shell_commands=lambda: [])

    def check_tool_output(*args, **kwds):
        return "ok"

    def prepare(self):
        self.prepare_called = True

    def set_external_id(self, external_id, **kwd):
        self.job.job_runner_external_id = external_id

    def get_command_line(self):
        return self.command_line

    def container_monitor_command(self, *args, **kwds):
        return None

    def check_for_entry_points(self):
        self.entry_points_checked = True

    def get_id_tag(self):
        return str(self.job_id)

    def get_state(self):
        return self.state

    def change_state(self, state, job=None):
        self.state = state

    @property
    def job_io(self):
        return bunch.Bunch(
            get_output_fnames=lambda: [],
            check_job_script_integrity=False,
            version_path="/tmp/version_path",
        )

    def get_job(self):
        return self.job

    def setup_external_metadata(self, **kwds):
        return self.metadata_command

    def get_env_setup_clause(self):
        return ""

    def has_limits(self):
        return False

    def fail(
        self,
        message,
        exception=False,
        tool_stdout="",
        tool_stderr="",
        exit_code=None,
        job_stdout=None,
        job_stderr=None,
    ):
        self.fail_message = message
        self.fail_exception = exception

    def finish(self, stdout, stderr, exit_code, **kwds):
        self.stdout = stdout
        self.stderr = stderr
        self.exit_code = exit_code

    def cleanup(self):
        self.cleanup_called = True

    def tmp_directory(self):
        return None

    def home_directory(self):
        return None

    def reclaim_ownership(self):
        pass

    @property
    def is_cwl_job(self):
        return False


# ---------------------------------------------------------------------------
# Helper: create events with ClassAd attributes (for hold codes, term signals)
# ---------------------------------------------------------------------------


def _set_job_events_with_classads(fake_htcondor, cjs, events):
    """Set events where each entry is a (event_name, classad_dict) tuple."""
    fake_htcondor.JobEventLog.set_events(
        cjs.user_log,
        [
            fake_htcondor.FakeJobEvent(int(cjs.job_id), 0, getattr(fake_htcondor.JobEventType, name), **attrs)
            for name, attrs in events
        ],
    )


# ---------------------------------------------------------------------------
# Regression tests for previously fixed bugs
# ---------------------------------------------------------------------------


def test_transient_status_error_resets_on_success(fake_instance, fake_htcondor, runner_factory, monkeypatch):
    """A transient error followed by a successful check resets status_error_count to 0."""
    runner = runner_factory()
    job_wrapper = _job_wrapper(fake_instance, 1, dict(htcondor_config="/tmp/condor-err-reset"))
    cjs = _watch_job(runner, job_wrapper)
    _write_user_log(cjs)

    call_count = 0
    original = runner._summarize_event_log

    def fail_once(c):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise OSError("simulated NFS timeout")
        return original(c)

    monkeypatch.setattr(runner, "_summarize_event_log", fail_once)

    # Cycle 1: error — counter goes to 1
    runner.check_watched_items()
    assert cjs.status_error_count == 1
    assert len(runner.watched) == 1

    # Cycle 2: success — counter must reset to 0
    runner.check_watched_items()
    assert cjs.status_error_count == 0
    assert len(runner.watched) == 1  # no terminal event yet, stays watched


def test_cleanup_job_always_at_submit_failure(fake_instance, fake_htcondor, runner_factory, monkeypatch):
    """cleanup_job='always' on the job wrapper is honoured when submit fails."""
    runner = runner_factory()
    job_wrapper = _job_wrapper(fake_instance, 1, dict(htcondor_config="/tmp/condor-cleanup-fail"))
    job_wrapper.cleanup_job = "always"

    client = runner._client_for_destination(job_wrapper.job_destination)
    monkeypatch.setattr(client, "submit", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("schedd down")))

    cleanup_calls = []
    monkeypatch.setattr(job_wrapper, "cleanup", lambda: cleanup_calls.append(True))

    cjs_cleanup_calls = []

    def patched_queue_job(jw):
        # Intercept cjs.cleanup — we can't get the cjs before queue_job creates it,
        # so patch HTCondorJobState.cleanup on the class temporarily.
        from galaxy.jobs.runners import htcondor as htcondor_module

        original_cleanup = htcondor_module.HTCondorJobState.cleanup

        def tracking_cleanup(self_cjs):
            cjs_cleanup_calls.append(True)
            original_cleanup(self_cjs)

        try:
            monkeypatch.setattr(htcondor_module.HTCondorJobState, "cleanup", tracking_cleanup)
            htcondor_module.HTCondorJobRunner.queue_job(runner, jw)
        finally:
            monkeypatch.setattr(htcondor_module.HTCondorJobState, "cleanup", original_cleanup)

    patched_queue_job(job_wrapper)

    assert hasattr(job_wrapper, "fail_message")
    assert cjs_cleanup_calls, "cjs.cleanup() should have been called with cleanup_job='always'"


def test_held_job_max_count_zero_disables_escalation(fake_instance, fake_htcondor, runner_factory):
    """max_held_count=0 disables hold escalation regardless of how many times the job is held."""
    runner = runner_factory()
    job_wrapper = _job_wrapper(fake_instance, 1, dict(htcondor_config="/tmp/condor-held-zero", max_held_count="0"))
    cjs = _watch_job(runner, job_wrapper)
    _write_user_log(cjs)

    for i in range(10):
        _set_job_events(fake_htcondor, cjs, ["JOB_HELD"])
        runner.check_watched_items()
        assert runner.work_queue.empty(), f"hold {i + 1} should not have escalated with max_held_count=0"
        assert len(runner.watched) == 1


@pytest.mark.parametrize(
    ("operation", "failing_method"),
    [
        pytest.param("submit", "submit", id="submit"),
        pytest.param("remove", "act", id="remove"),
    ],
)
def test_inprocess_client_evicts_stale_schedd_on_error(fake_instance, fake_htcondor, operation, failing_method):
    """_HTCondorInProcessClient evicts the cached Schedd when submit or remove raises."""
    from galaxy.jobs.runners.htcondor import _HTCondorInProcessClient

    client = _HTCondorInProcessClient(fake_htcondor)

    class FailingSchedd:
        def submit(self, *a, **k):
            raise RuntimeError("schedd lost connection")

        def act(self, *a, **k):
            raise RuntimeError("schedd lost connection")

    client._schedd_cache[(None, None)] = FailingSchedd()

    with pytest.raises(RuntimeError, match="schedd lost connection"):
        if operation == "submit":
            client.submit("executable = /bin/true\nqueue", None, None)
        else:
            client.remove(123, None, None)

    assert (None, None) not in client._schedd_cache, "stale entry should have been evicted on error"


# ---------------------------------------------------------------------------
# JOB_EVICTED lifecycle tests
# ---------------------------------------------------------------------------


def test_evicted_job_reexecutes_and_finishes(fake_instance, fake_htcondor, runner_factory):
    """A job that is evicted and rescheduled by HTCondor completes normally."""
    runner = runner_factory()
    job_wrapper = _job_wrapper(fake_instance, 1, dict(htcondor_config="/tmp/condor-evict-rerun"))
    cjs = _watch_job(runner, job_wrapper)
    _write_user_log(cjs)

    # Cycle 1: job runs then is evicted — running flag must clear
    _set_job_events(fake_htcondor, cjs, ["EXECUTE", "JOB_EVICTED"])
    runner.check_watched_items()
    assert len(runner.watched) == 1
    assert not runner.watched[0].running
    assert runner.work_queue.empty()

    # Cycle 2: HTCondor reschedules, job re-executes and terminates
    _set_job_events(fake_htcondor, cjs, ["EXECUTE", "JOB_TERMINATED"])
    runner.check_watched_items()
    assert len(runner.watched) == 0
    method, _ = runner.work_queue.get_nowait()
    assert method == runner.finish_job


def test_evicted_job_then_aborted_fails(fake_instance, fake_htcondor, runner_factory):
    """A job evicted and then aborted (HTCondor can't reschedule) is failed."""
    runner = runner_factory()
    job_wrapper = _job_wrapper(fake_instance, 1, dict(htcondor_config="/tmp/condor-evict-abort"))
    cjs = _watch_job(runner, job_wrapper)
    _write_user_log(cjs)

    # Cycle 1: evicted
    _set_job_events(fake_htcondor, cjs, ["EXECUTE", "JOB_EVICTED"])
    runner.check_watched_items()
    assert len(runner.watched) == 1

    # Cycle 2: aborted without re-execute
    _set_job_events(fake_htcondor, cjs, ["JOB_ABORTED"])
    runner.check_watched_items()
    assert len(runner.watched) == 0
    method, _ = runner.work_queue.get_nowait()
    assert method == runner.fail_job


# ---------------------------------------------------------------------------
# HoldReasonCode classification tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "hold_reason_code, expected_runner_state, message_fragment",
    [
        pytest.param(26, "memory_limit_reached", "memory", id="memory-hold-code-26"),
        pytest.param(34, "memory_limit_reached", "memory", id="memory-hold-code-34"),
        pytest.param(16, "walltime_reached", "run time", id="walltime-hold-code-16"),
    ],
)
def test_hold_reason_code_sets_runner_state(
    fake_instance,
    fake_htcondor,
    runner_factory,
    hold_reason_code,
    expected_runner_state,
    message_fragment,
):
    """JOB_HELD with a classified HoldReasonCode immediately fails with the correct runner_state."""
    runner = runner_factory()
    job_wrapper = _job_wrapper(fake_instance, 1, dict(htcondor_config=f"/tmp/condor-hold-code-{hold_reason_code}"))
    cjs = _watch_job(runner, job_wrapper)
    _write_user_log(cjs)

    _set_job_events_with_classads(fake_htcondor, cjs, [("JOB_HELD", {"HoldReasonCode": hold_reason_code})])
    runner.check_watched_items()

    assert len(runner.watched) == 0
    method, job_state_record = runner.work_queue.get_nowait()
    assert method == runner.fail_job
    assert job_state_record.runner_state == expected_runner_state
    assert message_fragment.lower() in job_state_record.fail_message.lower()


def test_hold_without_reason_code_uses_held_count_logic(fake_instance, fake_htcondor, runner_factory):
    """JOB_HELD with no HoldReasonCode (code 0) falls through to the existing held_count logic."""
    runner = runner_factory()
    job_wrapper = _job_wrapper(fake_instance, 1, dict(htcondor_config="/tmp/condor-hold-no-code"))
    cjs = _watch_job(runner, job_wrapper)
    _write_user_log(cjs)

    _set_job_events_with_classads(fake_htcondor, cjs, [("JOB_HELD", {})])
    runner.check_watched_items()

    # Generic hold with no classified code stays in watched (held_count < max)
    assert runner.work_queue.empty()
    assert len(runner.watched) == 1
    assert cjs.held_count == 1


# ---------------------------------------------------------------------------
# SIGKILL / OOM termination tests
# ---------------------------------------------------------------------------


def test_sigkill_termination_sets_memory_limit_runner_state(fake_instance, fake_htcondor, runner_factory):
    """JOB_TERMINATED with TerminatedNormally=False and TermSignal=9 is treated as OOM."""
    runner = runner_factory()
    job_wrapper = _job_wrapper(fake_instance, 1, dict(htcondor_config="/tmp/condor-sigkill"))
    cjs = _watch_job(runner, job_wrapper)
    _write_user_log(cjs)

    _set_job_events_with_classads(
        fake_htcondor, cjs, [("JOB_TERMINATED", {"TerminatedNormally": False, "TermSignal": 9})]
    )
    runner.check_watched_items()

    assert len(runner.watched) == 0
    method, job_state_record = runner.work_queue.get_nowait()
    assert method == runner.fail_job
    assert job_state_record.runner_state == "memory_limit_reached"
    assert "memory" in job_state_record.fail_message.lower()


def test_normal_termination_is_not_treated_as_oom(fake_instance, fake_htcondor, runner_factory):
    """JOB_TERMINATED with TerminatedNormally=True finishes normally, not as OOM."""
    runner = runner_factory()
    job_wrapper = _job_wrapper(fake_instance, 1, dict(htcondor_config="/tmp/condor-normal-term"))
    cjs = _watch_job(runner, job_wrapper)
    _write_user_log(cjs)

    _set_job_events_with_classads(
        fake_htcondor, cjs, [("JOB_TERMINATED", {"TerminatedNormally": True, "ReturnValue": 0})]
    )
    runner.check_watched_items()

    assert len(runner.watched) == 0
    method, _ = runner.work_queue.get_nowait()
    assert method == runner.finish_job


def test_non_9_signal_termination_finishes_normally(fake_instance, fake_htcondor, runner_factory):
    """JOB_TERMINATED killed by a non-SIGKILL signal is not classified as OOM."""
    runner = runner_factory()
    job_wrapper = _job_wrapper(fake_instance, 1, dict(htcondor_config="/tmp/condor-sig15"))
    cjs = _watch_job(runner, job_wrapper)
    _write_user_log(cjs)

    _set_job_events_with_classads(
        fake_htcondor, cjs, [("JOB_TERMINATED", {"TerminatedNormally": False, "TermSignal": 15})]
    )
    runner.check_watched_items()

    assert len(runner.watched) == 0
    method, _ = runner.work_queue.get_nowait()
    # SIGTERM is not OOM — finish_job reads the exit code to decide outcome
    assert method == runner.finish_job


def test_sigkill_on_user_stopped_job_finishes_not_oom(fake_instance, fake_htcondor, runner_factory):
    """SIGKILL on a STOPPED job is not OOM — user stopped it, complete normally."""
    runner = runner_factory()
    job_wrapper = _job_wrapper(
        fake_instance, 1, dict(htcondor_config="/tmp/condor-stopped-sigkill"), state=model.Job.states.STOPPED
    )
    cjs = _watch_job(runner, job_wrapper)
    _write_user_log(cjs)

    _set_job_events_with_classads(
        fake_htcondor, cjs, [("JOB_TERMINATED", {"TerminatedNormally": False, "TermSignal": 9})]
    )
    runner.check_watched_items()

    assert len(runner.watched) == 0
    method, _ = runner.work_queue.get_nowait()
    assert method == runner.finish_job


# ---------------------------------------------------------------------------
# Helper subprocess stderr drain test
# ---------------------------------------------------------------------------


def test_subprocess_client_restarts_after_helper_crash(fake_instance, fake_htcondor):
    """The subprocess client spawns a fresh helper process when the old one dies unexpectedly."""
    from galaxy.jobs.runners.htcondor import _HTCondorSubprocessClient

    client = _HTCondorSubprocessClient("/tmp/condor-subprocess-restart")
    try:
        # First submit triggers process spawn.
        client.submit("universe = vanilla\ngetenv = true\nnotification = NEVER\nqueue", None, None)
        first_process = client._process
        assert first_process is not None
        assert first_process.poll() is None  # alive

        # Simulate a crash.
        first_process.kill()
        first_process.wait()
        assert first_process.poll() is not None  # dead

        # Next submit must restart automatically and succeed.
        client.submit("universe = vanilla\ngetenv = true\nnotification = NEVER\nqueue", None, None)
        assert client._process is not first_process  # new process object
        assert client._process is not None
        assert client._process.poll() is None  # new process is alive
    finally:
        client.shutdown()


# ---------------------------------------------------------------------------
# Additional unit tests for helpers and edge cases
# ---------------------------------------------------------------------------


def test_normalize_condor_config_expands_and_resolves(tmp_path):
    from galaxy.jobs.runners.htcondor import _normalize_condor_config

    config_path = tmp_path / "condor.cfg"
    config_path.touch()
    result = _normalize_condor_config(str(config_path))
    assert result == os.path.realpath(str(config_path))
    assert "~" not in result


def test_condor_remove_missing_external_id_returns_error_string(fake_instance, fake_htcondor, runner_factory):
    """_condor_remove with no external_id returns an error string rather than raising."""
    runner = runner_factory()
    msg = runner._condor_remove(None, None)
    assert msg is not None
    assert "missing" in msg.lower()

    msg_empty = runner._condor_remove("", None)
    assert msg_empty is not None


def test_recover_unknown_state_does_not_add_to_monitor_queue(fake_instance, fake_htcondor, runner_factory):
    """recover() with an unexpected job state does not add anything to the monitor queue."""
    runner = runner_factory()
    job = model.Job()
    job.id = 42
    job.state = model.Job.states.ERROR
    job.job_runner_external_id = "999"
    job_wrapper = _job_wrapper(fake_instance, 42, dict(htcondor_config="/tmp/condor-unknown-state"))

    runner.recover(job, job_wrapper)

    assert runner.monitor_queue.empty()


def test_held_while_running_clears_running_flag(fake_instance, fake_htcondor, runner_factory):
    """A job that was running and then gets held must have running=False when it stays watched."""
    runner = runner_factory()
    job_wrapper = _job_wrapper(fake_instance, 1, dict(htcondor_config="/tmp/condor-held-from-running"))
    cjs = _watch_job(runner, job_wrapper)
    _write_user_log(cjs)

    # Simulate that the job was previously seen as running.
    cjs.running = True
    job_wrapper.state = model.Job.states.RUNNING

    _set_job_events(fake_htcondor, cjs, ["JOB_HELD"])
    runner.check_watched_items()

    assert len(runner.watched) == 1
    assert not runner.watched[0].running
    assert runner.work_queue.empty()


def test_locate_schedd_no_collector_no_name_returns_local_schedd(fake_htcondor):
    """_locate_schedd with no collector and no schedd_name uses Schedd() directly."""
    import threading

    from galaxy.jobs.runners.htcondor_helper import _locate_schedd

    cache: dict = {}
    lock = threading.Lock()
    schedd = _locate_schedd(fake_htcondor, cache, lock, None, None)
    assert schedd is not None
    assert (None, None) in cache
    assert cache[(None, None)] is schedd


def test_locate_schedd_caches_and_returns_same_object(fake_htcondor):
    """_locate_schedd returns the same object on a second call (cache hit)."""
    import threading

    from galaxy.jobs.runners.htcondor_helper import _locate_schedd

    cache: dict = {}
    lock = threading.Lock()
    first = _locate_schedd(fake_htcondor, cache, lock, None, None)
    second = _locate_schedd(fake_htcondor, cache, lock, None, None)
    assert first is second


def test_locate_schedd_with_collector_and_name(fake_htcondor):
    """_locate_schedd with a collector and explicit schedd_name locates via the collector."""
    import threading

    from galaxy.jobs.runners.htcondor_helper import _locate_schedd

    cache: dict = {}
    lock = threading.Lock()
    schedd = _locate_schedd(fake_htcondor, cache, lock, "collector:9618", "schedd@host")
    assert schedd is not None
    assert ("collector:9618", "schedd@host") in cache


# ---------------------------------------------------------------------------
# #1  stop_job with a container job
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# #2  _htcondor_params destination-vs-runner precedence
# ---------------------------------------------------------------------------


def test_htcondor_params_destination_overrides_runner(fake_instance, fake_htcondor, runner_factory):
    """Destination-level params take precedence over runner-level defaults."""
    runner = runner_factory()
    runner.runner_params.htcondor_collector = "runner_collector:9618"
    runner.runner_params.htcondor_schedd = "runner_schedd@host"
    runner.runner_params.htcondor_config = None

    dest = JobDestination(
        id="test",
        params=dict(
            htcondor_collector="dest_collector:9618",
            htcondor_schedd="dest_schedd@host",
            htcondor_config="/tmp/dest_config",
        ),
    )
    collector, schedd_name, condor_config = runner._htcondor_params(dest)

    assert collector == "dest_collector:9618"
    assert schedd_name == "dest_schedd@host"
    assert condor_config == os.path.realpath("/tmp/dest_config")


def test_htcondor_params_runner_default_used_when_destination_omits_params(
    fake_instance, fake_htcondor, runner_factory
):
    """Runner-level defaults are used when the destination dict has no htcondor_* keys."""
    runner = runner_factory()
    runner.runner_params.htcondor_collector = "runner_collector:9618"
    runner.runner_params.htcondor_schedd = "runner_schedd@host"
    runner.runner_params.htcondor_config = None

    dest = JobDestination(id="test", params={})
    collector, schedd_name, condor_config = runner._htcondor_params(dest)

    assert collector == "runner_collector:9618"
    assert schedd_name == "runner_schedd@host"
    assert condor_config is None


# ---------------------------------------------------------------------------
# #8  Missing event log after recovery (lost-log safety net)
# ---------------------------------------------------------------------------


def test_missing_event_log_escalates_to_failure_after_max_count(fake_instance, fake_htcondor, runner_factory):
    """A job whose event log is absent for MAX_MISSING_LOG_COUNT consecutive cycles is failed."""
    from galaxy.jobs.runners import htcondor as htcondor_module

    runner = runner_factory()
    job_wrapper = _job_wrapper(
        fake_instance,
        77,
        dict(htcondor_config="/tmp/condor-missing-log-escalate"),
        state=model.Job.states.RUNNING,
    )
    cjs = _watch_job(runner, job_wrapper)
    # Deliberately do NOT write the user log — simulates a log that was never created or was lost.
    assert not os.path.exists(cjs.user_log)

    max_count = htcondor_module.MAX_MISSING_LOG_COUNT

    for i in range(max_count - 1):
        runner.check_watched_items()
        assert len(runner.watched) == 1, f"job should still be watched after absent-log cycle {i + 1}"
        assert runner.work_queue.empty(), f"no failure should be queued after cycle {i + 1}"
        assert cjs.missing_log_count == i + 1

    # Final cycle: escalates to failure.
    runner.check_watched_items()
    assert len(runner.watched) == 0
    method, job_state_record = runner.work_queue.get_nowait()
    assert method == runner.fail_job
    assert "event log" in job_state_record.fail_message.lower()
    assert job_state_record.missing_log_count == max_count


def test_missing_log_count_resets_when_log_appears(fake_instance, fake_htcondor, runner_factory):
    """missing_log_count resets to 0 as soon as the event log becomes available."""
    runner = runner_factory()
    job_wrapper = _job_wrapper(fake_instance, 1, dict(htcondor_config="/tmp/condor-log-reappears"))
    cjs = _watch_job(runner, job_wrapper)
    assert not os.path.exists(cjs.user_log)

    # Two cycles with no log.
    runner.check_watched_items()
    assert cjs.missing_log_count == 1
    runner.check_watched_items()
    assert cjs.missing_log_count == 2

    # Log appears — counter resets and job stays watched (no terminal event yet).
    _write_user_log(cjs)
    runner.check_watched_items()
    assert cjs.missing_log_count == 0
    assert len(runner.watched) == 1


# ---------------------------------------------------------------------------
# GALAXY_SLOTS / GALAXY_MEMORY_MB injection
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected_mb"),
    [
        pytest.param("4096", 4096, id="plain-int-mb"),
        pytest.param("4G", 4096, id="suffix-G"),
        pytest.param("4GB", 4096, id="suffix-GB-two-letter"),
        pytest.param("2048K", 2, id="suffix-K-sub-mb"),
        pytest.param("1.5G", 1536, id="float"),
    ],
)
def test_parse_memory_mb_valid(value, expected_mb):
    from galaxy.jobs.runners.htcondor import _parse_memory_mb

    assert _parse_memory_mb(value) == expected_mb


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("$(MemoryGB) * 1024", id="classad-expression"),
        pytest.param("ifThenElse(True, 4096, 2048)", id="classad-function"),
        pytest.param("abc", id="garbage"),
    ],
)
def test_parse_memory_mb_unparseable_returns_none(value):
    from galaxy.jobs.runners.htcondor import _parse_memory_mb

    assert _parse_memory_mb(value) is None


# ---------------------------------------------------------------------------
# Walltime injection
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected_seconds"),
    [
        pytest.param("3600", 3600, id="plain-seconds"),
        pytest.param("90:00", 5400, id="MM:SS"),
        pytest.param("1:00:00", 3600, id="HH:MM:SS"),
        pytest.param("2:30:00", 9000, id="HH:MM:SS-nonzero-minutes"),
        pytest.param("1-0:00:00", 86400, id="D-HH:MM:SS"),
        pytest.param("1-12:00:00", 129600, id="D-HH:MM:SS-half-day"),
    ],
)
def test_parse_walltime_seconds_valid(value, expected_seconds):
    from galaxy.jobs.runners.htcondor import _parse_walltime_seconds

    assert _parse_walltime_seconds(value) == expected_seconds


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("garbage", id="garbage"),
        pytest.param("1:xx:00", id="non-numeric-field"),
        pytest.param("x-1:00:00", id="non-numeric-day"),
    ],
)
def test_parse_walltime_seconds_invalid_returns_none(value):
    from galaxy.jobs.runners.htcondor import _parse_walltime_seconds

    assert _parse_walltime_seconds(value) is None


def test_request_walltime_adds_periodic_hold(fake_instance, fake_htcondor, runner_factory):
    """request_walltime injects periodic_hold into the submit description."""
    runner = runner_factory()
    job_wrapper = _job_wrapper(
        fake_instance,
        1,
        dict(htcondor_config="/tmp/condor-walltime", request_walltime="3600"),
    )
    runner.queue_job(job_wrapper)

    records = _records(fake_instance, "submit")
    assert len(records) == 1
    assert "periodic_hold = (JobDurationSeconds >= 3600)" in records[0]["submit_description"]
    assert "request_walltime" not in records[0]["submit_description"]


def test_request_walltime_absent_no_periodic_hold(fake_instance, fake_htcondor, runner_factory):
    """No periodic_hold is injected when request_walltime is not set."""
    runner = runner_factory()
    job_wrapper = _job_wrapper(fake_instance, 1, dict(htcondor_config="/tmp/condor-no-walltime"))
    runner.queue_job(job_wrapper)

    records = _records(fake_instance, "submit")
    assert "periodic_hold" not in records[0]["submit_description"]


def test_request_walltime_does_not_override_user_periodic_hold(fake_instance, fake_htcondor, runner_factory):
    """A user-supplied periodic_hold expression takes precedence over request_walltime."""
    runner = runner_factory()
    job_wrapper = _job_wrapper(
        fake_instance,
        1,
        dict(
            htcondor_config="/tmp/condor-walltime-override",
            request_walltime="3600",
            periodic_hold="(JobDurationSeconds >= 7200)",
        ),
    )
    runner.queue_job(job_wrapper)

    records = _records(fake_instance, "submit")
    desc = records[0]["submit_description"]
    assert "periodic_hold = (JobDurationSeconds >= 7200)" in desc
    assert "periodic_hold = (JobDurationSeconds >= 3600)" not in desc


def test_galaxy_only_params_do_not_appear_in_submit_description(fake_instance, fake_htcondor, runner_factory):
    """Galaxy-internal destination parameters (max_held_count, embed_metadata_in_job) must not
    appear in the Condor submit description — HTCondor does not know about them."""
    runner = runner_factory()
    job_wrapper = _job_wrapper(
        fake_instance,
        1,
        dict(
            htcondor_config="/tmp/condor-galaxy-params",
            max_held_count="5",
            embed_metadata_in_job="false",
        ),
    )
    runner.queue_job(job_wrapper)

    records = _records(fake_instance, "submit")
    assert len(records) == 1
    desc = records[0]["submit_description"]
    assert "max_held_count" not in desc
    assert "embed_metadata_in_job" not in desc


# ---------------------------------------------------------------------------
# held_count reset on JOB_RELEASED
# ---------------------------------------------------------------------------


def test_held_count_resets_on_release(fake_instance, fake_htcondor, runner_factory):
    """held_count is reset to 0 when a JOB_RELEASED event is seen, so a job that is
    held-and-released multiple times does not accumulate toward max_held_count."""
    runner = runner_factory()
    # max_held_count=2 so we can verify the reset prevents premature failure.
    job_wrapper = _job_wrapper(fake_instance, 1, dict(htcondor_config="/tmp/condor-held-reset", max_held_count="2"))
    cjs = _watch_job(runner, job_wrapper)
    _write_user_log(cjs)

    # Cycle 1: held — held_count becomes 1
    _set_job_events(fake_htcondor, cjs, ["JOB_HELD"])
    runner.check_watched_items()
    assert cjs.held_count == 1
    assert runner.work_queue.empty()

    # Cycle 2: released — held_count must reset to 0
    _set_job_events(fake_htcondor, cjs, ["JOB_RELEASED"])
    runner.check_watched_items()
    assert cjs.held_count == 0
    assert runner.work_queue.empty()

    # Cycle 3: held again — held_count becomes 1 again (would be 2 without the reset,
    # which would trigger permanent failure with max_held_count=2)
    _set_job_events(fake_htcondor, cjs, ["JOB_HELD"])
    runner.check_watched_items()
    assert cjs.held_count == 1
    assert runner.work_queue.empty(), "should not fail — release reset the counter"
    assert len(runner.watched) == 1


# ---------------------------------------------------------------------------
# Subprocess client request timeout
# ---------------------------------------------------------------------------


def test_subprocess_client_times_out_on_hung_helper(fake_instance, fake_htcondor, monkeypatch):
    """If the helper process stops responding, _request raises RuntimeError after the timeout
    and marks the process as dead so the next call spawns a fresh helper."""
    import select as _select

    from galaxy.jobs.runners.htcondor import (
        _HTCondorSubprocessClient,
        HTCONDOR_HELPER_TIMEOUT,
    )

    client = _HTCondorSubprocessClient("/tmp/condor-timeout-test")

    # Patch select.select to simulate a timeout (no file descriptors ready).
    def fake_select(rlist, wlist, xlist, timeout):
        return [], [], []

    monkeypatch.setattr(_select, "select", fake_select)

    # Trigger process creation by accessing the client internals, then call _request.
    with client._lock:
        client._ensure_process_locked()
    original_process = client._process
    assert original_process is not None

    with pytest.raises(RuntimeError, match=str(HTCONDOR_HELPER_TIMEOUT)):
        client.submit("universe = vanilla\nqueue", None, None)

    # The hung process must have been killed and the reference cleared.
    assert original_process.poll() is not None, "hung process should have been killed"
    assert client._process is None, "process reference should be cleared for respawn"
