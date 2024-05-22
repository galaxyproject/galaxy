"""Integration tests for the Pulsar embedded runner with outputs written back to Galaxy via TUS."""

import os
import tempfile

from galaxy.util import safe_makedirs
from galaxy_test.driver import integration_util

JOB_CONF_TEMPLATE = """
runners:
  local:
    load: galaxy.jobs.runners.local:LocalJobRunner
  pulsar_embed:
    load: galaxy.jobs.runners.pulsar:PulsarEmbeddedJobRunner
    pulsar_app_config:
      tool_dependency_dir: none
      conda_auto_init: false
      conda_auto_install: false

execution:
  default: pulsar_embed
  environments:
    local:
      runner: local
    pulsar_embed:
      runner: pulsar_embed
      default_file_action: remote_transfer_tus

tools:
- class: local
  environment: local
"""


class EmbeddedPulsarTargetingTusIntegrationInstance(integration_util.IntegrationInstance):
    """Describe a Galaxy test instance with embedded pulsar configured to target job files tus."""

    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        jobs_directory = os.path.join(cls._test_driver.mkdtemp(), "pulsar_staging")
        safe_makedirs(jobs_directory)
        with tempfile.NamedTemporaryFile(suffix="_tus_job_conf.yml", mode="w", delete=False) as job_conf:
            job_conf.write(JOB_CONF_TEMPLATE)
        config["job_config_file"] = job_conf.name
        infrastructure_url = "http://localhost:$GALAXY_WEB_PORT"
        config["galaxy_infrastructure_url"] = infrastructure_url


instance = integration_util.integration_module_instance(EmbeddedPulsarTargetingTusIntegrationInstance)

test_tools = integration_util.integration_tool_runner(["simple_constructs", "composite_output_tests"])
