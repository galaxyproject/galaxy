import os

from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util
from .test_containerized_jobs import (
    disable_dependency_resolution,
    MulledJobTestCases,
    skip_if_container_type_unavailable,
)

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
EMBEDDED_PULSAR_JOB_CONFIG_FILE_SINGULARITY = os.path.join(SCRIPT_DIRECTORY, "embedded_pulsar_singularity_job_conf.yml")
EMBEDDED_PULSAR_JOB_CONFIG_FILE_DOCKER = os.path.join(SCRIPT_DIRECTORY, "embedded_pulsar_docker_job_conf.yml")


class BaseEmbeddedPulsarContainerIntegrationTestCase(integration_util.IntegrationTestCase):
    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        cls.jobs_directory = cls._test_driver.mkdtemp()
        config["jobs_directory"] = cls.jobs_directory
        config["job_config_file"] = cls.job_config_file
        disable_dependency_resolution(config)

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.history_id = self.dataset_populator.new_history()

    @classmethod
    def setUpClass(cls):
        skip_if_container_type_unavailable(cls)
        super().setUpClass()


class EmbeddedSingularityPulsarIntegrationTestCase(BaseEmbeddedPulsarContainerIntegrationTestCase, MulledJobTestCases):
    # singularity passes $HOME by default
    default_container_home_dir = os.environ.get("HOME", "/")
    job_config_file = EMBEDDED_PULSAR_JOB_CONFIG_FILE_SINGULARITY
    container_type = "singularity"


class EmbeddedDockerPulsarIntegrationTestCase(BaseEmbeddedPulsarContainerIntegrationTestCase, MulledJobTestCases):
    job_config_file = EMBEDDED_PULSAR_JOB_CONFIG_FILE_DOCKER
    container_type = "docker"


instance = integration_util.integration_module_instance(EmbeddedSingularityPulsarIntegrationTestCase)

test_tools = integration_util.integration_tool_runner(
    [
        "tool_directory_docker",
    ]
)
