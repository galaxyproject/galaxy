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
    dataset_populator: DatasetPopulator
    job_config_file: str
    jobs_directory: str
    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        super().handle_galaxy_config_kwds(config)
        cls.jobs_directory = cls._test_driver.mkdtemp()
        config["jobs_directory"] = cls.jobs_directory
        config["job_config_file"] = cls.job_config_file
        disable_dependency_resolution(config)

    def setUp(self) -> None:
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    @classmethod
    def setUpClass(cls) -> None:
        skip_if_container_type_unavailable(cls)
        super().setUpClass()


class TestEmbeddedSingularityPulsarIntegration(BaseEmbeddedPulsarContainerIntegrationTestCase, MulledJobTestCases):
    dataset_populator: DatasetPopulator
    # singularity passes $HOME by default
    default_container_home_dir = os.environ.get("HOME", "/")
    job_config_file = EMBEDDED_PULSAR_JOB_CONFIG_FILE_SINGULARITY
    container_type = "singularity"


class TestEmbeddedDockerPulsarIntegration(BaseEmbeddedPulsarContainerIntegrationTestCase, MulledJobTestCases):
    dataset_populator: DatasetPopulator
    job_config_file = EMBEDDED_PULSAR_JOB_CONFIG_FILE_DOCKER
    container_type = "docker"


instance = integration_util.integration_module_instance(TestEmbeddedSingularityPulsarIntegration)

test_tools = integration_util.integration_tool_runner(
    [
        "tool_directory_docker",
    ]
)
