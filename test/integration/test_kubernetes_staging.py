"""Integration tests for Kubernetes pod staging.

This case is way more brittle than the other integration tests distributed with Galaxy.
This is because it requires Kubernetes, RabbitMQ, and the test itself needs to know what
the test host IP address will be relative to a container inside Kubernetes in order to
communicate job status updates back.

For this reason, this test will only work out of the box currently with Docker for Mac,
rabbitmq installed via Homebrew, and if a fixed port is set for the test.

   GALAXY_TEST_PORT=9234 pytest test/integration/test_kubernetes_staging.py

"""
import os
import string
import tempfile

from base import integration_util  # noqa: I100,I202
from base.populators import skip_without_tool
from .test_containerized_jobs import EXTENDED_TIMEOUT, MulledJobTestCases  # noqa: I201
from .test_job_environments import BaseJobEnvironmentIntegrationTestCase  # noqa: I201

TOOL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, 'tools'))
AMQP_URL = os.environ.get("GALAXY_TEST_AMQP_URL", "amqp://guest:guest@localhost:5672//")
GALAXY_TEST_KUBERNETES_INFRASTRUCTURE_HOST = os.environ.get("GALAXY_TEST_KUBERNETES_INFRASTRUCTURE_HOST", "host.docker.internal")


CONTAINERIZED_TEMPLATE = """
runners:
  local:
    load: galaxy.jobs.runners.local:LocalJobRunner
    workers: 1
  pulsar_k8s:
    load: galaxy.jobs.runners.pulsar:PulsarKubernetesJobRunner
    galaxy_url: ${infrastructure_url}
    amqp_url: ${amqp_url}

execution:
  default: pulsar_k8s_environment
  environments:
    pulsar_k8s_environment:
      k8s_config_path: ${k8s_config_path}
      runner: pulsar_k8s
      docker_enabled: true
      docker_default_container_id: busybox:ubuntu-14.04
      pulsar_app_config:
        message_queue_url: '${container_amqp_url}'
      env:
        - name: SOME_ENV_VAR
          value: '42'
    local_environment:
      runner: local
tools:
  - id: upload1
    environment: local_environment
"""


DEPENDENCY_RESOLUTION_TEMPLATE = """
runners:
  local:
    load: galaxy.jobs.runners.local:LocalJobRunner
    workers: 1
  pulsar_k8s:
    load: galaxy.jobs.runners.pulsar:PulsarKubernetesJobRunner
    galaxy_url: ${infrastructure_url}
    amqp_url: ${amqp_url}

execution:
  default: pulsar_k8s_environment
  environments:
    pulsar_k8s_environment:
      k8s_config_path: ${k8s_config_path}
      runner: pulsar_k8s
      pulsar_app_config:
        message_queue_url: '${container_amqp_url}'
      env:
        - name: SOME_ENV_VAR
          value: '42'
    local_environment:
      runner: local
tools:
  - id: upload1
    environment: local_environment
"""


def job_config(template_str, jobs_directory):
    job_conf_template = string.Template(template_str)
    port = os.environ.get('GALAXY_TEST_PORT')
    assert port
    infrastructure_url = "http://%s:%s" % (GALAXY_TEST_KUBERNETES_INFRASTRUCTURE_HOST, port)
    container_amqp_url = to_infrastructure_uri(AMQP_URL)
    job_conf_str = job_conf_template.substitute(jobs_directory=jobs_directory,
                                                tool_directory=TOOL_DIR,
                                                k8s_config_path=integration_util.k8s_config_path(),
                                                amqp_url=AMQP_URL,
                                                container_amqp_url=container_amqp_url,
                                                infrastructure_url=infrastructure_url,
                                                )
    with tempfile.NamedTemporaryFile(suffix="_kubernetes_integration_job_conf.yml", mode="w", delete=False) as job_conf:
        job_conf.write(job_conf_str)
    return job_conf.name


@integration_util.skip_unless_kubernetes()
@integration_util.skip_unless_fixed_port()
class KubernetesStagingContainerIntegrationTestCase(BaseJobEnvironmentIntegrationTestCase, MulledJobTestCases):

    def setUp(self):
        super(KubernetesStagingContainerIntegrationTestCase, self).setUp()
        self.history_id = self.dataset_populator.new_history()

    @classmethod
    def setUpClass(cls):
        # realpath for docker deployed in a VM on Mac, also done in driver_util.
        cls.jobs_directory = os.path.realpath(tempfile.mkdtemp())
        super(KubernetesStagingContainerIntegrationTestCase, cls).setUpClass()

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["jobs_directory"] = cls.jobs_directory
        config["file_path"] = cls.jobs_directory
        config["job_config_file"] = job_config(CONTAINERIZED_TEMPLATE, cls.jobs_directory)
        config["default_job_shell"] = '/bin/sh'
        # Disable local tool dependency resolution.
        config["tool_dependency_dir"] = "none"

    @skip_without_tool("job_environment_default")
    def test_job_environment(self):
        job_env = self._run_and_get_environment_properties()
        assert job_env.some_env == '42'


@integration_util.skip_unless_kubernetes()
@integration_util.skip_unless_fixed_port()
class KubernetesDependencyResolutionIntegrationTestCase(BaseJobEnvironmentIntegrationTestCase, MulledJobTestCases):

    def setUp(self):
        super(KubernetesDependencyResolutionIntegrationTestCase, self).setUp()
        self.history_id = self.dataset_populator.new_history()

    @classmethod
    def setUpClass(cls):
        # realpath for docker deployed in a VM on Mac, also done in driver_util.
        cls.jobs_directory = os.path.realpath(tempfile.mkdtemp())
        super(KubernetesDependencyResolutionIntegrationTestCase, cls).setUpClass()

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["jobs_directory"] = cls.jobs_directory
        config["file_path"] = cls.jobs_directory
        config["job_config_file"] = job_config(DEPENDENCY_RESOLUTION_TEMPLATE, cls.jobs_directory)

        config["default_job_shell"] = '/bin/sh'
        # Disable tool dependency resolution.
        config["tool_dependency_dir"] = "none"
        config["enable_beta_mulled_containers"] = "true"

    def test_mulled_simple(self):
        self.dataset_populator.run_tool("mulled_example_simple", {}, self.history_id)
        self.dataset_populator.wait_for_history(self.history_id, assert_ok=True)
        output = self.dataset_populator.get_history_dataset_content(self.history_id, timeout=EXTENDED_TIMEOUT)
        assert "0.7.15-r1140" in output


def to_infrastructure_uri(uri):
    # remap MQ or file server URI hostnames for in-container versions, this is sloppy
    # should actually parse the URI and rebuild with correct host
    # similar code found in Pulsar integration_tests.py.
    infrastructure_uri = uri
    if GALAXY_TEST_KUBERNETES_INFRASTRUCTURE_HOST:
        if "0.0.0.0" in infrastructure_uri:
            infrastructure_uri = infrastructure_uri.replace("0.0.0.0", GALAXY_TEST_KUBERNETES_INFRASTRUCTURE_HOST)
        elif "localhost" in infrastructure_uri:
            infrastructure_uri = infrastructure_uri.replace("localhost", GALAXY_TEST_KUBERNETES_INFRASTRUCTURE_HOST)
        elif "127.0.0.1" in infrastructure_uri:
            infrastructure_uri = infrastructure_uri.replace("127.0.0.1", GALAXY_TEST_KUBERNETES_INFRASTRUCTURE_HOST)
    return infrastructure_uri
