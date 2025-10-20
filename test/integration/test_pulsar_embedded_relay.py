"""Integration tests for the Pulsar embedded runner with outputs to working directory."""

import os
import string
import tempfile
import uuid

from galaxy.util import safe_makedirs
from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util
from galaxy_test.driver.integration_util import (
    docker_run,
    docker_rm,
)


SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
EMBEDDED_PULSAR_JOB_CONFIG_FILE = os.path.join(SCRIPT_DIRECTORY, "embedded_pulsar_mq_job_conf.yml")
AMQP_URL = os.environ.get("GALAXY_TEST_PULSAR_RELAY")

JOB_CONF_TEMPLATE = """
runners:
  local:
    load: galaxy.jobs.runners.local:LocalJobRunner
    workers: 1
  pulsar:
    load: galaxy.jobs.runners.pulsar:PulsarEmbeddedMQJobRunner
    pulsar_app_config:
      tool_dependency_dir: none
      conda_auto_init: false
      conda_auto_install: false
      message_queue_url: ${amqp_url}
      message_queue_username: admin
      message_queue_password: ${relay_password}
      staging_directory: ${jobs_directory}
    relay_url: ${amqp_url}
    relay_username: admin
    relay_password: ${relay_password}
execution:
  default: pulsar_mq_environment
  environments:
    pulsar_mq_environment:
      runner: pulsar
      rewrite_parameters: true
      dependency_resolution: none
      default_file_action: remote_transfer
      jobs_directory: ${jobs_directory}
      remote_metadata: true
      remote_property_galaxy_home: ${galaxy_home}
    local_environment:
      runner: local
tools:
  - id: __DATA_FETCH__
    environment: local_environment
"""


def _handle_galaxy_config_kwds(cls, config):
    random_password = uuid.uuid4().hex
    docker_run(
        "mvdbeek/pulsar-relay",
        cls.container_name,
        env_vars={"PULSAR_BOOTSTRAP_ADMIN_USERNAME": "admin", "PULSAR_BOOTSTRAP_ADMIN_PASSWORD": random_password},
        remove=False,
        ports=[(9001, 8080)],
    )
    jobs_directory = os.path.join(cls._test_driver.mkdtemp(), "pulsar_staging")
    safe_makedirs(jobs_directory)
    job_conf_template = string.Template(JOB_CONF_TEMPLATE)
    job_conf_str = job_conf_template.substitute(
        amqp_url="http://localhost:9001",
        jobs_directory=jobs_directory,
        galaxy_home=os.path.join(SCRIPT_DIRECTORY, os.pardir),
        relay_password=random_password,
    )
    with tempfile.NamedTemporaryFile(suffix="_mq_job_conf.yml", mode="w", delete=False) as job_conf:
        job_conf.write(job_conf_str)
    config["job_config_file"] = job_conf.name
    infrastructure_url = "http://localhost:$GALAXY_WEB_PORT"
    config["galaxy_infrastructure_url"] = infrastructure_url


class EmbeddedPulsarRelayIntegrationInstance(integration_util.IntegrationInstance):
    """Describe a Galaxy test instance with embedded pulsar configured.

    $ Setup RabbitMQ (e.g. https://www.rabbitmq.com/install-homebrew.html)
    $ GALAXY_TEST_AMQP_URL='amqp://guest:guest@localhost:5672//' pytest -s test/integration/test_pulsar_embedded_mq.py
    """

    container_name = "pulsar-relay"
    dataset_populator: DatasetPopulator
    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        _handle_galaxy_config_kwds(cls, config)

    @classmethod
    def tearDownClass(cls):
        try:
            super().tearDownClass()
        finally:
            docker_rm(cls.container_name)


instance = integration_util.integration_module_instance(EmbeddedPulsarRelayIntegrationInstance)

test_tools = integration_util.integration_tool_runner(
    ["simple_constructs", "composite_output_tests", "all_output_types"]
)
