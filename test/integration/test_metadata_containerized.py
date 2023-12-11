import os
import subprocess

from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util
from galaxy_test.driver.driver_util import galaxy_root
from .test_containerized_jobs import (
    disable_dependency_resolution,
    skip_if_container_type_unavailable,
)

DOCKERIZED_JOB_CONFIG = {
    "runners": {"local": {"load": "galaxy.jobs.runners.local:LocalJobRunner", "workers": 1}},
    "execution": {
        "default": "local_docker",
        "environments": {
            "local_docker": {
                "runner": "local",
                "docker_enabled": True,
                "metadata_config": {
                    "containerize": True,
                    "engine": "docker",
                    "image": "galaxyproject/galaxy-job-execution",
                },
            },
        },
    },
}


class ContainerizedMetadataIntegrationTestCase(integration_util.IntegrationTestCase):
    dataset_populator: DatasetPopulator
    framework_tool_and_types = True
    container_type = "docker"

    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        super().handle_galaxy_config_kwds(config)
        config["job_config"] = DOCKERIZED_JOB_CONFIG
        config["enable_celery_tasks"] = False
        config["metadata_strategy"] = "extended"
        disable_dependency_resolution(config)

    def setUp(self) -> None:
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    @classmethod
    def setUpClass(cls) -> None:
        skip_if_container_type_unavailable(cls)
        subprocess.check_output(
            [
                "docker",
                "build",
                "-t",
                "galaxyproject/galaxy-job-execution",
                "-f",
                os.path.join(galaxy_root, "packages", "job_execution", "Dockerfile"),
                galaxy_root,
            ]
        )
        super().setUpClass()


instance = integration_util.integration_module_instance(ContainerizedMetadataIntegrationTestCase)

test_tools = integration_util.integration_tool_runner(
    [
        "metadata_bam",
    ]
)
