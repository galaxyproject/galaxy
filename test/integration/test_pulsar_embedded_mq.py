"""Integration tests for the Pulsar embedded runner with outputs to working directory."""

import os
import string
import tempfile

import pytest

from galaxy.util import safe_makedirs
from galaxy_test.driver import integration_util

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
EMBEDDED_PULSAR_JOB_CONFIG_FILE = os.path.join(SCRIPT_DIRECTORY, "embedded_pulsar_mq_job_conf.yml")
AMQP_URL = os.environ.get("GALAXY_TEST_AMQP_URL", "amqp://guest:guest@localhost:5672//")

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
      staging_directory: ${jobs_directory}
    amqp_url: ${amqp_url}
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
  - id: upload1
    environment: local_environment
"""


class EmbeddedMessageQueuePulsarIntegrationInstance(integration_util.IntegrationInstance):
    """Describe a Galaxy test instance with embedded pulsar configured.

    $ Setup RabbitMQ (e.g. https://www.rabbitmq.com/install-homebrew.html)
    $ GALAXY_TEST_AMQP_URL='amqp://guest:guest@localhost:5672//' pytest -s test/integration/test_pulsar_embedded_mq.py
    """

    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        amqp_url = os.environ.get("GALAXY_TEST_AMQP_URL", None)
        if amqp_url is None:
            pytest.skip("External AMQP URL not configured for test")

        jobs_directory = os.path.join(cls._test_driver.mkdtemp(), "pulsar_staging")
        safe_makedirs(jobs_directory)
        job_conf_template = string.Template(JOB_CONF_TEMPLATE)
        job_conf_str = job_conf_template.substitute(
            amqp_url=AMQP_URL, jobs_directory=jobs_directory, galaxy_home=os.path.join(SCRIPT_DIRECTORY, os.pardir)
        )
        with tempfile.NamedTemporaryFile(suffix="_mq_job_conf.yml", mode="w", delete=False) as job_conf:
            job_conf.write(job_conf_str)
        config["job_config_file"] = job_conf.name
        infrastructure_url = "http://localhost:$GALAXY_WEB_PORT"
        config["galaxy_infrastructure_url"] = infrastructure_url


instance = integration_util.integration_module_instance(EmbeddedMessageQueuePulsarIntegrationInstance)

test_tools = integration_util.integration_tool_runner(["simple_constructs"])
