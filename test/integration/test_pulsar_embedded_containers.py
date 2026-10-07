import os

from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util
from .test_containerized_jobs import (
    build_metadata_container,
    disable_dependency_resolution,
    EXTENDED_TIMEOUT,
    MulledJobTestCases,
    skip_if_container_type_unavailable,
)

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
EMBEDDED_PULSAR_JOB_CONFIG_FILE_SINGULARITY = os.path.join(SCRIPT_DIRECTORY, "embedded_pulsar_singularity_job_conf.yml")
EMBEDDED_PULSAR_JOB_CONFIG_FILE_DOCKER = os.path.join(SCRIPT_DIRECTORY, "embedded_pulsar_docker_job_conf.yml")
FAKE_BWA_OUTPUT = "fake bwa from galaxy_packages"


class BaseEmbeddedPulsarContainerIntegrationTestCase(integration_util.IntegrationTestCase):
    dataset_populator: DatasetPopulator
    job_config_file: str
    jobs_directory: str
    container_type: str
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
        if cls.container_type == "docker":
            build_metadata_container()
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


def write_fake_bwa_package(dependency_dir: str, marker_path: str) -> None:
    """Lay out a galaxy_packages bwa 0.7.15 whose env.sh records each time it is sourced."""
    package_dir = os.path.join(dependency_dir, "bwa", "0.7.15")
    bin_dir = os.path.join(package_dir, "bin")
    os.makedirs(bin_dir)
    with open(os.path.join(package_dir, "env.sh"), "w") as f:
        f.write(f'echo sourced >> "{marker_path}"\nPATH="$PACKAGE_BASE/bin:$PATH"\nexport PATH\n')
    fake_bwa = os.path.join(bin_dir, "bwa")
    with open(fake_bwa, "w") as f:
        f.write(f"#!/bin/sh\necho '{FAKE_BWA_OUTPUT}'\n")
    os.chmod(fake_bwa, 0o755)


class TestEmbeddedDockerPulsarRemoteDependencyResolution(integration_util.IntegrationTestCase):
    """Pulsar-side (``dependency_resolution: remote``) resolution is skipped for containerized jobs."""

    dataset_populator: DatasetPopulator
    container_type = "docker"
    framework_tool_and_types = True
    marker_path: str

    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        super().handle_galaxy_config_kwds(config)
        disable_dependency_resolution(config)
        dependency_dir = cls._test_driver.mkdtemp()
        cls.marker_path = os.path.join(cls._test_driver.mkdtemp(), "env_sh_sourced")
        write_fake_bwa_package(dependency_dir, cls.marker_path)
        config.pop("job_config_file", None)
        config["job_config"] = {
            "runners": {
                "local": {"load": "galaxy.jobs.runners.local:LocalJobRunner"},
                "pulsar_embed": {
                    "load": "galaxy.jobs.runners.pulsar:PulsarEmbeddedJobRunner",
                    "pulsar_app_config": {
                        "tool_dependency_dir": dependency_dir,
                        "dependency_resolvers": [{"type": "galaxy_packages"}],
                        "conda_auto_init": False,
                        "conda_auto_install": False,
                    },
                },
            },
            "execution": {
                "default": "pulsar_docker",
                "environments": {
                    "local": {"runner": "local"},
                    "pulsar_docker": {
                        "runner": "pulsar_embed",
                        "remote_metadata": True,
                        "docker_enabled": True,
                        "docker_sudo": False,
                        "require_container": True,
                    },
                    "pulsar_host": {"runner": "pulsar_embed", "remote_metadata": True},
                },
            },
            "tools": [
                {"id": "upload1", "environment": "local"},
                {"id": "mulled_example_simple", "environment": "pulsar_host"},
            ],
        }

    @classmethod
    def setUpClass(cls) -> None:
        skip_if_container_type_unavailable(cls)
        super().setUpClass()

    def setUp(self) -> None:
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def test_host_job_resolves_dependencies_in_pulsar(self, history_id: str) -> None:
        # Control: proves the env.sh fixture is reached under remote resolution.
        sourced_before = self._env_sh_sourced_count()
        output = self._run_and_get_contents("mulled_example_simple", history_id)
        assert FAKE_BWA_OUTPUT in output
        assert self._env_sh_sourced_count() > sourced_before

    def test_container_job_skips_dependency_resolution_in_pulsar(self, history_id: str) -> None:
        sourced_before = self._env_sh_sourced_count()
        output = self._run_and_get_contents("mulled_example_explicit", history_id)
        assert "0.7.15-r1140" in output
        assert self._env_sh_sourced_count() == sourced_before

    def _run_and_get_contents(self, tool_id: str, history_id: str) -> str:
        run_response = self.dataset_populator.run_tool(tool_id, {}, history_id)
        self.dataset_populator.wait_for_job(run_response["jobs"][0]["id"], assert_ok=True, timeout=EXTENDED_TIMEOUT)
        return self.dataset_populator.get_history_dataset_content(
            history_id, content_id=run_response["outputs"][0]["id"]
        )

    def _env_sh_sourced_count(self) -> int:
        if not os.path.exists(self.marker_path):
            return 0
        with open(self.marker_path) as f:
            return len(f.readlines())


instance = integration_util.integration_module_instance(TestEmbeddedSingularityPulsarIntegration)

test_tools = integration_util.integration_tool_runner(
    [
        "tool_directory_docker",
    ]
)
