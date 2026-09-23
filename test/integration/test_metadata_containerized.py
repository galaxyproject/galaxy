import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from sqlalchemy import select

from galaxy import model
from galaxy.job_execution.setup import JobWorkingDirectory
from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util
from .test_containerized_jobs import (
    build_metadata_container,
    disable_dependency_resolution,
    skip_if_container_type_unavailable,
)

METADATA_IMAGE = "galaxyproject/galaxy-job-execution:integration-marker"
METADATA_MARKER = "metadata_container_marker"


def build_marked_metadata_container():
    # Only this image creates the marker. Host-side metadata cannot satisfy the assertion.
    with TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "galaxy-set-metadata").write_text(
            "#!/venv/bin/python\n"
            "from pathlib import Path\n"
            "from galaxy.metadata.set_metadata import set_metadata\n"
            "set_metadata()\n"
            f"Path('metadata/{METADATA_MARKER}').write_text('container executed')\n"
        )
        (root / "Dockerfile").write_text(
            "FROM galaxyproject/galaxy-job-execution:integration\n"
            "COPY --chmod=755 galaxy-set-metadata /venv/bin/galaxy-set-metadata\n"
        )
        subprocess.check_output(["docker", "build", "-t", METADATA_IMAGE, directory], stderr=subprocess.STDOUT)


DOCKERIZED_METADATA_JOB_CONFIG = {
    "runners": {
        "local": {"load": "galaxy.jobs.runners.local:LocalJobRunner"},
        "pulsar_embed": {
            "load": "galaxy.jobs.runners.pulsar:PulsarEmbeddedJobRunner",
            "pulsar_app_config": {"conda_auto_init": False, "conda_auto_install": False},
        },
    },
    "execution": {
        "default": "local_docker",
        "environments": {
            "local_docker": {
                "runner": "local",
                "docker_enabled": True,
                "metadata_strategy": "extended",
                "outputs_to_working_directory": True,
                "metadata_config": {
                    "containerize": True,
                    "engine": "docker",
                    "image": METADATA_IMAGE,
                },
            },
            "pulsar_embed": {
                "runner": "pulsar_embed",
                "docker_enabled": True,
                "remote_metadata": True,
                # Return outputs through Pulsar staging; extended metadata writes
                # directly to the object store and requires remote access to it.
                "metadata_strategy": "directory",
                "default_file_action": "copy",
                "metadata_config": {
                    "containerize": True,
                    "engine": "docker",
                    "image": METADATA_IMAGE,
                },
            },
        },
    },
    "tools": [
        {"id": "metadata_bam", "environment": "local_docker"},
        {"id": "composite_output", "environment": "pulsar_embed"},
    ],
}


class ContainerizedMetadataIntegrationTestCase(integration_util.IntegrationTestCase):
    dataset_populator: DatasetPopulator
    framework_tool_and_types = True
    container_type = "docker"

    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        super().handle_galaxy_config_kwds(config)
        config["job_config"] = DOCKERIZED_METADATA_JOB_CONFIG
        config["enable_celery_tasks"] = False
        config["metadata_strategy"] = "extended"
        config["retry_metadata_internally"] = False
        config["cleanup_job"] = "never"
        disable_dependency_resolution(config)

    def setUp(self) -> None:
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    @classmethod
    def setUpClass(cls) -> None:
        skip_if_container_type_unavailable(cls)
        build_metadata_container()
        build_marked_metadata_container()
        super().setUpClass()


instance = integration_util.integration_module_instance(ContainerizedMetadataIntegrationTestCase)


@pytest.mark.parametrize("tool_id", ["metadata_bam", "composite_output"])
def test_tools(instance, tool_id):
    instance._run_tool_test(tool_id)
    job = instance._app.model.session.scalars(select(model.Job).filter_by(tool_id=tool_id)).one()
    directory = JobWorkingDirectory(job, instance._app.object_store).resolve()
    assert directory is not None
    # Pulsar must return this file through metadata staging, without shared storage.
    assert (Path(directory) / "metadata" / METADATA_MARKER).read_text() == "container executed"
