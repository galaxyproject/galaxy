"""Integration tests for Kubernetes pod staging.

This case is way more brittle than the other integration tests distributed with Galaxy.
This is because it requires Kubernetes, RabbitMQ, and the test itself needs to know what
the test host IP address will be relative to a container inside Kubernetes in order to
communicate job status updates back.

For this reason, this test will only work out of the box currently with Docker for Mac,
rabbitmq installed via Homebrew, and if a fixed port is set for the test.

   GALAXY_TEST_PORT=9234 pytest test/integration/test_coexecution.py

"""

import os
import platform
import random
import string
import tempfile
import time
from typing import (
    Any,
    Dict,
)

import yaml

from galaxy.jobs.runners.util.pykube_util import (
    Job,
    pykube_client_from_dict,
)
from galaxy_test.base.populators import (
    DatasetPopulator,
    skip_without_tool,
)
from galaxy_test.driver import integration_util
from .test_containerized_jobs import (
    EXTENDED_TIMEOUT,
    MulledJobTestCases,
)
from .test_job_environments import BaseJobEnvironmentIntegrationTestCase
from .test_kubernetes_runner import KubernetesDatasetPopulator
from .test_local_job_cancellation import CancelsJob

TOOL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, "tools"))
GALAXY_TEST_INFRASTRUCTURE_HOST = os.environ.get("GALAXY_TEST_INFRASTRUCTURE_HOST", "_PLATFORM_AUTO_")
AMQP_URL = integration_util.AMQP_URL
GALAXY_TEST_KUBERNETES_NAMESPACE = os.environ.get("GALAXY_TEST_K8S_NAMESPACE", "default")


CONTAINERIZED_TEMPLATE = """
runners:
  local:
    load: galaxy.jobs.runners.local:LocalJobRunner
    workers: 1
  pulsar_k8s:
    load: galaxy.jobs.runners.pulsar:PulsarKubernetesJobRunner
    amqp_url: ${amqp_url}

execution:
  default: pulsar_k8s_environment
  environments:
    pulsar_k8s_environment:
      k8s_config_path: ${k8s_config_path}
      k8s_galaxy_instance_id: ${instance_id}
      k8s_namespace: ${k8s_namespace}
      runner: pulsar_k8s
      docker_enabled: true
      docker_default_container_id: busybox:1.36.1-glibc
      pulsar_app_config:
        message_queue_url: '${container_amqp_url}'
      env:
        - name: SOME_ENV_VAR
          value: '42'
    local_environment:
      runner: local
tools:
  - id: __DATA_FETCH__
    environment: local_environment
"""


DEPENDENCY_RESOLUTION_TEMPLATE = """
runners:
  local:
    load: galaxy.jobs.runners.local:LocalJobRunner
    workers: 1
  pulsar_k8s:
    load: galaxy.jobs.runners.pulsar:PulsarKubernetesJobRunner
    amqp_url: ${amqp_url}

execution:
  default: pulsar_k8s_environment
  environments:
    pulsar_k8s_environment:
      k8s_config_path: ${k8s_config_path}
      k8s_galaxy_instance_id: ${instance_id}
      k8s_namespace: ${k8s_namespace}
      runner: pulsar_k8s
      pulsar_app_config:
        message_queue_url: '${container_amqp_url}'
      env:
        - name: SOME_ENV_VAR
          value: '42'
    local_environment:
      runner: local
tools:
  - id: __DATA_FETCH__
    environment: local_environment
"""


def job_config(template_str: str, jobs_directory: str) -> str:
    job_conf_template = string.Template(template_str)
    assert AMQP_URL
    container_amqp_url = to_infrastructure_uri(AMQP_URL)
    instance_id = "".join(random.choice(string.ascii_lowercase) for i in range(8))
    job_conf_str = job_conf_template.substitute(
        jobs_directory=jobs_directory,
        tool_directory=TOOL_DIR,
        instance_id=instance_id,
        k8s_config_path=integration_util.k8s_config_path(),
        k8s_namespace=GALAXY_TEST_KUBERNETES_NAMESPACE,
        amqp_url=AMQP_URL,
        container_amqp_url=container_amqp_url,
    )
    with tempfile.NamedTemporaryFile(suffix="_kubernetes_integration_job_conf.yml", mode="w", delete=False) as job_conf:
        job_conf.write(job_conf_str)
    return job_conf.name


TES_CONTAINERIZED_TEMPLATE = """
runners:
  local:
    load: galaxy.jobs.runners.local:LocalJobRunner
    workers: 1
  pulsar_tes:
    load: galaxy.jobs.runners.pulsar:PulsarTesJobRunner
    amqp_url: ${amqp_url}

execution:
  default: pulsar_tes_environment
  environments:
    pulsar_tes_environment:
      runner: pulsar_tes
      tes_url: ${tes_url}
      docker_enabled: true
      docker_default_container_id: busybox:1.36.1-glibc
      pulsar_app_config:
        message_queue_url: '${container_amqp_url}'
      env:
        - name: SOME_ENV_VAR
          value: '42'
    local_environment:
      runner: local
tools:
  - id: __DATA_FETCH__
    environment: local_environment
"""


TES_DEPENDENCY_RESOLUTION_TEMPLATE = """
runners:
  local:
    load: galaxy.jobs.runners.local:LocalJobRunner
    workers: 1
  pulsar_tes:
    load: galaxy.jobs.runners.pulsar:PulsarTesJobRunner
    amqp_url: ${amqp_url}

execution:
  default: pulsar_tes_environment
  environments:
    pulsar_tes_environment:
      tes_url: ${tes_url}
      runner: pulsar_tes
      pulsar_app_config:
        message_queue_url: '${container_amqp_url}'
      env:
        - name: SOME_ENV_VAR
          value: '42'
    local_environment:
      runner: local
tools:
  - id: __DATA_FETCH__
    environment: local_environment
"""


TES_CONTAINERIZED_TEMPLATE_CUSTOM_AMQP_KEY = """
runners:
  local:
    load: galaxy.jobs.runners.local:LocalJobRunner
    workers: 1
  pulsar_tes:
    load: galaxy.jobs.runners.pulsar:PulsarTesJobRunner
    amqp_url: ${amqp_url}
    amqp_key_prefix: pulsar_foobar34_

execution:
  default: pulsar_tes_environment
  environments:
    pulsar_tes_environment:
      runner: pulsar_tes
      tes_url: ${tes_url}
      docker_enabled: true
      docker_default_container_id: busybox:1.36.1-glibc
      pulsar_app_config:
        message_queue_url: '${container_amqp_url}'
      env:
        - name: SOME_ENV_VAR
          value: '42'
    local_environment:
      runner: local
tools:
  - id: __DATA_FETCH__
    environment: local_environment
"""


def tes_job_config(template_str: str, jobs_directory: str) -> str:
    job_conf_template = string.Template(template_str)
    assert AMQP_URL
    container_amqp_url = to_infrastructure_uri(AMQP_URL)
    instance_id = "".join(random.choice(string.ascii_lowercase) for i in range(8))
    tes_url = os.environ.get("FUNNEL_SERVER_TARGET")
    job_conf_str = job_conf_template.substitute(
        jobs_directory=jobs_directory,
        tool_directory=TOOL_DIR,
        instance_id=instance_id,
        tes_url=tes_url,
        amqp_url=AMQP_URL,
        container_amqp_url=container_amqp_url,
    )
    with tempfile.NamedTemporaryFile(suffix="_tes_integration_job_conf.yml", mode="w", delete=False) as job_conf:
        job_conf.write(job_conf_str)
    return job_conf.name


@integration_util.skip_unless_amqp()
@integration_util.skip_if_github_workflow()
class TestCoexecution(BaseJobEnvironmentIntegrationTestCase, MulledJobTestCases):
    dataset_populator: DatasetPopulator
    jobs_directory: str

    def setUp(self) -> None:
        super().setUp()
        self.dataset_populator = KubernetesDatasetPopulator(self.galaxy_interactor)

    @classmethod
    def setUpClass(cls) -> None:
        # realpath for docker deployed in a VM on Mac, also done in driver_util.
        cls.jobs_directory = os.path.realpath(tempfile.mkdtemp())
        super().setUpClass()


@integration_util.skip_unless_kubernetes()
class TestKubernetesStagingContainerIntegration(CancelsJob, TestCoexecution):
    dataset_populator: DatasetPopulator
    job_config_file: str

    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        config["jobs_directory"] = cls.jobs_directory
        config["file_path"] = cls.jobs_directory
        cls.job_config_file = job_config(CONTAINERIZED_TEMPLATE, cls.jobs_directory)
        config["job_config_file"] = cls.job_config_file
        config["default_job_shell"] = "/bin/sh"
        # Disable local tool dependency resolution.
        config["tool_dependency_dir"] = "none"
        set_infrastucture_url(config)

    @property
    def instance_id(self) -> str:
        with open(self.job_config_file) as fh:
            config = yaml.safe_load(fh)
        return config["execution"]["environments"]["pulsar_k8s_environment"]["k8s_galaxy_instance_id"]

    @skip_without_tool("cat_data_and_sleep")
    def test_job_cancel(self) -> None:
        with self.dataset_populator.test_history() as history_id:
            job_id = self._setup_cat_data_and_sleep(history_id)
            self._wait_for_job_running(job_id)

            assert self._active_kubernetes_jobs == 1

            delete_response = self.dataset_populator.cancel_job(job_id)
            assert delete_response.json() is True

            time.sleep(5)

            assert self._active_kubernetes_jobs == 0

    @skip_without_tool("job_environment_default")
    def test_job_environment(self) -> None:
        job_env = self._run_and_get_environment_properties()
        assert job_env.some_env == "42"

    @property
    def _active_kubernetes_jobs(self) -> int:
        pykube_api = pykube_client_from_dict({})
        # TODO: namespace.
        jobs = Job.objects(pykube_api).filter()
        active = 0
        for job in jobs:
            if self.instance_id not in job.obj["metadata"]["name"]:
                continue
            status = job.obj["status"]
            active += status.get("active", 0)
        return active


@integration_util.skip_unless_kubernetes()
class TestKubernetesDependencyResolutionIntegration(TestCoexecution):
    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        config["jobs_directory"] = cls.jobs_directory
        config["file_path"] = cls.jobs_directory
        config["job_config_file"] = job_config(DEPENDENCY_RESOLUTION_TEMPLATE, cls.jobs_directory)

        config["default_job_shell"] = "/bin/sh"
        # Disable tool dependency resolution.
        config["tool_dependency_dir"] = "none"
        set_infrastucture_url(config)

    def test_mulled_simple(self, history_id: str) -> None:
        self.dataset_populator.run_tool("mulled_example_simple", {}, history_id)
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        output = self.dataset_populator.get_history_dataset_content(history_id, timeout=EXTENDED_TIMEOUT)
        assert "0.7.15-r1140" in output


@integration_util.skip_unless_environ("FUNNEL_SERVER_TARGET")
class TestTesCoexecutionContainerIntegration(TestCoexecution):
    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        config["jobs_directory"] = cls.jobs_directory
        config["file_path"] = cls.jobs_directory
        config["job_config_file"] = tes_job_config(TES_CONTAINERIZED_TEMPLATE, cls.jobs_directory)

        config["default_job_shell"] = "/bin/sh"
        # Disable tool dependency resolution.
        config["tool_dependency_dir"] = "none"
        set_infrastucture_url(config)


@integration_util.skip_unless_environ("FUNNEL_SERVER_TARGET")
class TestTesCoexecutionCustomAmqpKeyContainerIntegration(TestCoexecution):
    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        config["jobs_directory"] = cls.jobs_directory
        config["file_path"] = cls.jobs_directory
        config["job_config_file"] = tes_job_config(TES_CONTAINERIZED_TEMPLATE_CUSTOM_AMQP_KEY, cls.jobs_directory)

        config["default_job_shell"] = "/bin/sh"
        # Disable tool dependency resolution.
        config["tool_dependency_dir"] = "none"
        set_infrastucture_url(config)


@integration_util.skip_unless_environ("FUNNEL_SERVER_TARGET")
class TestTesDependencyResolutionIntegration(TestCoexecution):
    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        config["jobs_directory"] = cls.jobs_directory
        config["file_path"] = cls.jobs_directory
        config["job_config_file"] = tes_job_config(TES_DEPENDENCY_RESOLUTION_TEMPLATE, cls.jobs_directory)

        config["default_job_shell"] = "/bin/sh"
        # Disable tool dependency resolution.
        config["tool_dependency_dir"] = "none"
        set_infrastucture_url(config)

    def test_mulled_simple(self, history_id: str) -> None:
        self.dataset_populator.run_tool("mulled_example_simple", {}, history_id)
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        output = self.dataset_populator.get_history_dataset_content(history_id, timeout=EXTENDED_TIMEOUT)
        assert "0.7.15-r1140" in output


def set_infrastucture_url(config: Dict[str, Any]) -> None:
    hostname = to_infrastructure_uri("0.0.0.0")
    infrastructure_url = f"http://{hostname}:$GALAXY_WEB_PORT"
    config["galaxy_infrastructure_url"] = infrastructure_url


def to_infrastructure_uri(uri: str) -> str:
    # remap MQ or file server URI hostnames for in-container versions, this is sloppy
    # should actually parse the URI and rebuild with correct host
    # Copied from Pulsar's integraiton tests.
    infrastructure_host = GALAXY_TEST_INFRASTRUCTURE_HOST
    if infrastructure_host == "_PLATFORM_AUTO_":
        system = platform.system()
        if system in ["Darwin", "Windows"]:
            # assume Docker Desktop is installed and use its domain
            infrastructure_host = "host.docker.internal"
        else:
            # native linux Docker sometimes sets up
            infrastructure_host = "172.17.0.1"

    infrastructure_uri = uri
    if infrastructure_host:
        if "0.0.0.0" in infrastructure_uri:
            infrastructure_uri = infrastructure_uri.replace("0.0.0.0", infrastructure_host)
        elif "localhost" in infrastructure_uri:
            infrastructure_uri = infrastructure_uri.replace("localhost", infrastructure_host)
        elif "127.0.0.1" in infrastructure_uri:
            infrastructure_uri = infrastructure_uri.replace("127.0.0.1", infrastructure_host)
    return infrastructure_uri
