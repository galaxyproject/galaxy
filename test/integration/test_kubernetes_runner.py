"""Integration tests for the Kubernetes runner."""

# Tested on docker for mac 18.06.1-ce-mac73 using the default kubernetes setup,
# also works on minikube
import collections
import json
import os
import shlex
import string
import subprocess
import tempfile
import time
from typing import (
    List,
    Optional,
    overload,
)

import pytest
from typing_extensions import Literal

from galaxy.model import Job
from galaxy.tool_util.verify.wait import timeout_type
from galaxy.util import unicodify
from galaxy_test.base.populators import (
    DatasetPopulator,
    DEFAULT_TIMEOUT,
    skip_without_tool,
    wait_on,
)
from galaxy_test.driver import integration_util
from .test_containerized_jobs import MulledJobTestCases
from .test_job_environments import BaseJobEnvironmentIntegrationTestCase

PERSISTENT_VOLUME_NAME = "pv-galaxy-integration-test"
PERSISTENT_VOLUME_CLAIM_NAME = "galaxy-pvc-integration-test"
Config = collections.namedtuple("Config", "path")
TOOL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, "tools"))


class KubeSetupConfigTuple(Config):
    def setup(self) -> None:
        subprocess.check_call(["kubectl", "create", "-f", self.path])

    def teardown(self) -> None:
        subprocess.check_call(["kubectl", "delete", "-f", self.path])


def persistent_volume(path: str, persistent_volume_name: str) -> KubeSetupConfigTuple:
    volume_yaml = string.Template(
        """
kind: PersistentVolume
apiVersion: v1
metadata:
  name: $persistent_volume_name
  labels:
    type: local
spec:
  capacity:
    storage: 5Gi
  accessModes:
    - ReadWriteMany
  persistentVolumeReclaimPolicy: Retain
  storageClassName: manual
  local:
    path: $path
  nodeAffinity:
    required:
      nodeSelectorTerms:
      - matchExpressions:
        - key: app
          operator: NotIn
          values:
            - 'i-do-not-exist'
    """
    ).substitute(path=path, persistent_volume_name=persistent_volume_name)
    with tempfile.NamedTemporaryFile(suffix="_persistent_volume.yml", mode="w", delete=False) as volume:
        volume.write(volume_yaml)
    return KubeSetupConfigTuple(path=volume.name)


def persistent_volume_claim(persistent_volume_name: str, persistent_volum_claim_name: str) -> KubeSetupConfigTuple:
    peristent_volume_claim_yaml = string.Template(
        """
kind: PersistentVolumeClaim
apiVersion: v1
metadata:
  name: $persistent_volume_claim_name
spec:
  accessModes:
    - ReadWriteMany
  volumeName: $persistent_volume_name
  resources:
    requests:
      storage: 2Gi
  storageClassName: manual
"""
    ).substitute(
        persistent_volume_name=persistent_volume_name, persistent_volume_claim_name=persistent_volum_claim_name
    )
    with tempfile.NamedTemporaryFile(suffix="_persistent_volume_claim.yml", mode="w", delete=False) as volume_claim:
        volume_claim.write(peristent_volume_claim_yaml)
    return KubeSetupConfigTuple(path=volume_claim.name)


def job_config(jobs_directory: str) -> Config:
    job_conf_template = string.Template(
        """<job_conf>
    <plugins>
        <plugin id="local" type="runner" load="galaxy.jobs.runners.local:LocalJobRunner" workers="2"/>
        <plugin id="k8s" type="runner" load="galaxy.jobs.runners.kubernetes:KubernetesJobRunner">
            <param id="k8s_persistent_volume_claims">jobs-directory-claim:$jobs_directory,tool-directory-claim:$tool_directory</param>
            <param id="k8s_config_path">$k8s_config_path</param>
            <param id="k8s_galaxy_instance_id">gx-short-id</param>
            <param id="k8s_run_as_user_id">$$uid</param>
        </plugin>
        <plugin id="k8s_walltime_short" type="runner" load="galaxy.jobs.runners.kubernetes:KubernetesJobRunner">
            <param id="k8s_persistent_volume_claims">jobs-directory-claim:$jobs_directory,tool-directory-claim:$tool_directory</param>
            <param id="k8s_config_path">$k8s_config_path</param>
            <param id="k8s_galaxy_instance_id">gx-short-id</param>
            <param id="k8s_walltime_limit">10</param>
            <param id="k8s_run_as_user_id">$$uid</param>
        </plugin>
        <plugin id="k8s_no_cleanup" type="runner" load="galaxy.jobs.runners.kubernetes:KubernetesJobRunner">
            <param id="k8s_persistent_volume_claims">jobs-directory-claim:$jobs_directory,tool-directory-claim:$tool_directory</param>
            <param id="k8s_config_path">$k8s_config_path</param>
            <param id="k8s_galaxy_instance_id">gx-short-id</param>
            <param id="k8s_cleanup_job">never</param>
            <param id="k8s_run_as_user_id">$$uid</param>
        </plugin>
    </plugins>
    <destinations default="k8s_destination">
        <destination id="k8s_destination" runner="k8s">
            <param id="limits_cpu">1.1</param>
            <param id="limits_memory">100M</param>
            <param id="docker_enabled">true</param>
            <param id="docker_default_container_id">busybox:1.36.1-glibc</param>
            <env id="SOME_ENV_VAR">42</env>
        </destination>
        <destination id="k8s_destination_walltime_short" runner="k8s_walltime_short">
            <param id="limits_cpu">1.1</param>
            <param id="limits_memory">100M</param>
            <param id="docker_enabled">true</param>
            <param id="docker_default_container_id">busybox:1.36.1-glibc</param>
            <env id="SOME_ENV_VAR">42</env>
        </destination>
        <destination id="k8s_destination_no_cleanup" runner="k8s_no_cleanup">
            <param id="limits_cpu">1.1</param>
            <param id="limits_memory">100M</param>
            <param id="docker_enabled">true</param>
            <param id="docker_default_container_id">busybox:1.36.1-glibc</param>
            <env id="SOME_ENV_VAR">42</env>
        </destination>
        <destination id="local_dest" runner="local">
        </destination>
    </destinations>
    <tools>
        <tool id="__DATA_FETCH__" destination="local_dest"/>
        <tool id="create_2" destination="k8s_destination_walltime_short"/>
        <tool id="galaxy_slots_and_memory" destination="k8s_destination_no_cleanup"/>
    </tools>
</job_conf>
"""
    )
    job_conf_str = job_conf_template.substitute(
        jobs_directory=jobs_directory,
        tool_directory=TOOL_DIR,
        k8s_config_path=integration_util.k8s_config_path(),
    )
    with tempfile.NamedTemporaryFile(suffix="_kubernetes_integration_job_conf.xml", mode="w", delete=False) as job_conf:
        job_conf.write(job_conf_str)
    return Config(job_conf.name)


class KubernetesDatasetPopulator(DatasetPopulator):
    def wait_for_history(
        self, history_id: str, assert_ok: bool = False, timeout: timeout_type = DEFAULT_TIMEOUT
    ) -> str:
        try:
            return super().wait_for_history(history_id, assert_ok, timeout)
        except AssertionError:
            print(
                "Kubernetes status:\n {}".format(unicodify(subprocess.check_output(["kubectl", "describe", "nodes"])))
            )
            raise


@integration_util.skip_unless_kubernetes()
class TestKubernetesIntegration(BaseJobEnvironmentIntegrationTestCase, MulledJobTestCases):
    dataset_populator: KubernetesDatasetPopulator
    job_config: Config
    jobs_directory: str
    persistent_volume_claims: List[KubeSetupConfigTuple]
    persistent_volumes: List[KubeSetupConfigTuple]
    container_type = "docker"

    def setUp(self) -> None:
        super().setUp()
        self.dataset_populator = KubernetesDatasetPopulator(self.galaxy_interactor)

    @classmethod
    def setUpClass(cls) -> None:
        # realpath for docker deployed in a VM on Mac, also done in driver_util.
        cls.jobs_directory = os.path.realpath(tempfile.mkdtemp())
        volumes = [
            (cls.jobs_directory, "jobs-directory-volume", "jobs-directory-claim"),
            (TOOL_DIR, "tool-directory-volume", "tool-directory-claim"),
        ]
        cls.persistent_volumes = []
        cls.persistent_volume_claims = []
        for path, volume, claim in volumes:
            volume_obj = persistent_volume(path, volume)
            volume_obj.setup()
            cls.persistent_volumes.append(volume_obj)
            claim_obj = persistent_volume_claim(volume, claim)
            claim_obj.setup()
            cls.persistent_volume_claims.append(claim_obj)
        cls.job_config = job_config(jobs_directory=cls.jobs_directory)
        super().setUpClass()

    @classmethod
    def tearDownClass(cls) -> None:
        for claim in cls.persistent_volume_claims:
            claim.teardown()
        for volume in cls.persistent_volumes:
            volume.teardown()
        super().tearDownClass()

    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        # TODO: implement metadata setting as separate job, as service or side-car
        super().handle_galaxy_config_kwds(config)
        config["jobs_directory"] = cls.jobs_directory
        config["file_path"] = cls.jobs_directory
        config["job_config_file"] = cls.job_config.path
        config["default_job_shell"] = "/bin/sh"
        # Disable tool dependency resolution.
        config["tool_dependency_dir"] = "none"

    @pytest.mark.xfail(reason="mktemp -d does not work in default kubernetes setup")
    @skip_without_tool("job_environment_default")
    def test_job_environment(self) -> None:
        job_env = self._run_and_get_environment_properties()
        assert job_env.some_env == "42"

    @staticmethod
    def _wait_for_external_state(sa_session, job, expected) -> None:
        # Not checking the state here allows the change from queued to running to overwrite
        # the change from queued to deleted_new in the API thread - this is a problem because
        # the job will still run. See issue https://github.com/galaxyproject/galaxy/issues/4960.
        max_tries = 60
        while max_tries > 0 and job.job_runner_external_id is None or job.state != expected:
            sa_session.refresh(job)
            time.sleep(1)
            max_tries -= 1

    @skip_without_tool("cat_data_and_sleep")
    def test_kill_process(self) -> None:
        with self.dataset_populator.test_history() as history_id:
            hda1 = self.dataset_populator.new_dataset(history_id, content="1 2 3")
            running_inputs = {
                "input1": {"src": "hda", "id": hda1["id"]},
                "sleep_time": 240,
            }
            running_response = self.dataset_populator.run_tool(
                "cat_data_and_sleep",
                running_inputs,
                history_id,
            )
            job_dict = running_response["jobs"][0]

            app = self._app
            sa_session = app.model.session
            job = sa_session.get(Job, app.security.decode_id(job_dict["id"]))
            assert job
            self._wait_for_external_state(sa_session, job, Job.states.RUNNING)
            assert not job.finished

            external_id = job.job_runner_external_id
            assert external_id
            output = unicodify(subprocess.check_output(["kubectl", "get", "job", external_id, "-o", "json"]))
            status = json.loads(output)
            assert status["status"]["active"] == 1

            delete_response = self.dataset_populator.cancel_job(job_dict["id"])
            assert delete_response.json() is True

            # Wait for job to be cancelled in kubernetes
            time.sleep(2)
            # The default job config removes jobs, didn't find a better way to check that the job doesn't exist anymore
            with pytest.raises(subprocess.CalledProcessError) as excinfo:
                subprocess.check_output(["kubectl", "get", "job", external_id, "-o", "json"], stderr=subprocess.STDOUT)
            assert "not found" in unicodify(excinfo.value.output)

    @skip_without_tool("cat_data_and_sleep")
    def test_external_job_delete(self) -> None:
        with self.dataset_populator.test_history() as history_id:
            hda1 = self.dataset_populator.new_dataset(history_id, content="1 2 3")
            running_inputs = {
                "input1": {"src": "hda", "id": hda1["id"]},
                "sleep_time": 240,
            }
            running_response = self.dataset_populator.run_tool_raw(
                "cat_data_and_sleep",
                running_inputs,
                history_id,
            )
            job_dict = running_response.json()["jobs"][0]

            app = self._app
            sa_session = app.model.session
            job = sa_session.get(Job, app.security.decode_id(job_dict["id"]))
            assert job
            self._wait_for_external_state(sa_session, job, Job.states.RUNNING)

            external_id = job.job_runner_external_id
            assert external_id
            output = unicodify(subprocess.check_output(["kubectl", "get", "job", external_id, "-o", "json"]))
            status = json.loads(output)
            assert status["status"]["active"] == 1

            output = unicodify(subprocess.check_output(["kubectl", "delete", "job", external_id, "-o", "name"]))
            assert f"job.batch/{external_id}" in output

            result = self.dataset_populator.wait_for_tool_run(
                run_response=running_response, history_id=history_id, assert_ok=False
            ).json()
            details = self.dataset_populator.get_job_details(result["jobs"][0]["id"], full=True).json()

            assert details["state"] == Job.states.ERROR, details

    @skip_without_tool("job_properties")
    def test_exit_code_127(self, history_id: str) -> None:
        inputs = {
            "failbool": True,
            "sleepsecs": 5,
        }
        running_response = self.dataset_populator.run_tool_raw(
            "job_properties",
            inputs,
            history_id,
        )
        # check that logs are also available in job logs
        app = self._app
        job_id = app.security.decode_id(running_response.json()["jobs"][0]["id"])
        sa_session = app.model.session
        job = sa_session.get(Job, job_id)
        assert job
        self._wait_for_external_state(sa_session=sa_session, job=job, expected=Job.states.RUNNING)

        external_id = job.job_runner_external_id

        @overload
        def get_kubectl_logs(allow_wait: Literal[False]) -> str: ...

        @overload
        def get_kubectl_logs(allow_wait: bool = True) -> Optional[str]: ...

        def get_kubectl_logs(allow_wait: bool = True) -> Optional[str]:
            log_cmd = ["kubectl", "logs", "-l", f"job-name={external_id}"]
            p = subprocess.run(log_cmd, capture_output=True, text=True)
            if p.returncode:
                if allow_wait and "is waiting to start" in p.stderr:
                    return None
                raise Exception(
                    f"Command '{shlex.join(log_cmd)}' failed with exit code: {p.returncode}.\nstdout: {p.stdout}\nstderr: {p.stderr}"
                )
            return p.stdout

        wait_on(get_kubectl_logs, "k8s logs")
        output = get_kubectl_logs(allow_wait=False)

        EXPECTED_STDOUT = "The bool is not true"
        EXPECTED_STDERR = "The bool is very not true"
        assert EXPECTED_STDOUT in output
        assert EXPECTED_STDERR in output
        # Wait for job to finish, then fetch details via Galaxy API
        result = self.dataset_populator.wait_for_tool_run(
            run_response=running_response, history_id=history_id, assert_ok=False
        ).json()
        details = self.dataset_populator.get_job_details(result["jobs"][0]["id"], full=True).json()
        assert details["state"] == "error", details
        assert details["stdout"].strip() == EXPECTED_STDOUT, details
        assert details["stderr"].strip() == EXPECTED_STDERR, details
        assert details["exit_code"] == 127, details

    @skip_without_tool("Count1")
    def test_python_dep(self, history_id) -> None:
        hda1 = self.dataset_populator.new_dataset(history_id, content="1\t2\t3", file_type="tabular", wait=True)
        self.dataset_populator.run_tool(
            "Count1",
            {"input": {"src": "hda", "id": hda1["id"]}, "column": [1]},
            history_id,
        )

    @skip_without_tool("galaxy_slots_and_memory")
    def test_slots_and_memory(self, history_id: str) -> None:
        running_response = self.dataset_populator.run_tool(
            "galaxy_slots_and_memory",
            {},
            history_id,
        )
        dataset_content = self.dataset_populator.get_history_dataset_content(history_id, hid=1).strip()
        CPU = "2"
        MEM = "100"
        MEM_PER_SLOT = "50"
        assert [CPU, MEM, MEM_PER_SLOT] == dataset_content.split("\n"), dataset_content

        # Tool is mapped to destination without cleanup, make sure job still exists in kubernetes API
        job_dict = running_response["jobs"][0]
        job = self.galaxy_interactor.get("jobs/{}".format(job_dict["id"]), admin=True).json()
        external_id = job["external_id"]
        output = unicodify(subprocess.check_output(["kubectl", "get", "job", external_id, "-o", "json"]))
        status = json.loads(output)
        assert "active" not in status["status"]

    @skip_without_tool("create_2")
    def test_walltime_limit(self, history_id: str) -> None:
        running_response = self.dataset_populator.run_tool_raw(
            "create_2",
            {"sleep_time": 60},
            history_id,
        )
        result = self.dataset_populator.wait_for_tool_run(
            run_response=running_response, history_id=history_id, assert_ok=False
        ).json()
        details = self.dataset_populator.get_job_details(result["jobs"][0]["id"], full=True).json()
        assert details["state"] == "error"
        hda_details = self.dataset_populator.get_history_dataset_details(history_id, assert_ok=False)
        assert hda_details["misc_info"] == "Job was active longer than specified deadline"
