import os
import uuid

from galaxy.tool_util_models import UserToolSource
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


def _home_probe_tool(probe_name: str) -> dict:
    return {
        "class": "GalaxyUserTool",
        "id": "home_probe",
        "name": "home_probe",
        "version": "0.1",
        "container": "busybox:1.36.1-glibc",
        "shell_command": f'echo "$HOME" > home.txt && echo "$PWD" > pwd.txt && touch "$HOME/{probe_name}"',
        "outputs": [
            {"name": "home", "type": "data", "format": "txt", "from_work_dir": "home.txt"},
            {"name": "pwd", "type": "data", "format": "txt", "from_work_dir": "pwd.txt"},
        ],
    }


class BaseEmbeddedPulsarContainerIntegrationTestCase(integration_util.IntegrationTestCase):
    dataset_populator: DatasetPopulator
    job_config_file: str
    jobs_directory: str
    container_type: str
    pulsar_staging_directory: str
    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        super().handle_galaxy_config_kwds(config)
        cls.jobs_directory = cls._test_driver.mkdtemp()
        cls.pulsar_staging_directory = os.path.join(config["data_dir"], "pulsar_staging")
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

    def test_user_defined_tool_home_is_working_directory(self) -> None:
        probe_name = f"home_probe_{uuid.uuid4().hex}"
        host_probe = os.path.join(os.environ["HOME"], probe_name)
        try:
            with (
                self.dataset_populator.test_history() as history_id,
                self.dataset_populator.user_tool_execute_permissions(),
            ):
                tool = self.dataset_populator.create_unprivileged_tool(UserToolSource(**_home_probe_tool(probe_name)))
                response = self.dataset_populator.run_tool_raw(None, {}, history_id, tool_uuid=tool["uuid"]).json()
                self.dataset_populator.wait_for_job(response["jobs"][0]["id"], assert_ok=True, timeout=EXTENDED_TIMEOUT)
                outputs = {output["output_name"]: output["id"] for output in response["outputs"]}
                home, pwd = (
                    self.dataset_populator.get_history_dataset_content(history_id, content_id=outputs[name]).strip()
                    for name in ("home", "pwd")
                )
            assert not os.path.exists(host_probe)
        finally:
            if os.path.exists(host_probe):
                os.unlink(host_probe)
        assert home == pwd
        assert home.startswith(self.pulsar_staging_directory)
        assert home.endswith("/working")


class TestEmbeddedSingularityPulsarIntegration(BaseEmbeddedPulsarContainerIntegrationTestCase, MulledJobTestCases):
    dataset_populator: DatasetPopulator
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
