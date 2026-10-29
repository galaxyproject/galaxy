from types import SimpleNamespace
from typing import (
    cast,
    TYPE_CHECKING,
)

import pytest

from galaxy.jobs import MinimalJobWrapper
from galaxy.jobs.runners import BaseJobRunner

if TYPE_CHECKING:
    from galaxy.app import GalaxyManagerApplication


def _job_wrapper(tool_type="default", require_container="False"):
    tool = SimpleNamespace(
        tool_type=tool_type,
        containers=[],
        requirements=[],
        requires_galaxy_python_environment=False,
        docker_env_pass_through=[],
        id="cat",
        version="1.0",
        profile=24.0,
        tool_dir="/tools/cat",
    )
    destination_params = {"require_container": require_container}
    job_wrapper = SimpleNamespace(
        tool=tool,
        guest_ports=None,
        working_directory="/jobs/000/1",
        tool_working_directory="/jobs/000/1/working",
        tmp_directory=lambda: None,
        home_directory=lambda: None,
        job_destination=SimpleNamespace(params=destination_params, tool_env_names=[]),
        get_destination_configuration=lambda key, default=None: destination_params.get(key, default),
    )
    requires_containerization = cast(property, MinimalJobWrapper.requires_containerization).fget
    assert requires_containerization
    job_wrapper.requires_containerization = requires_containerization(job_wrapper)
    return job_wrapper


def _runner_without_containers():
    runner = BaseJobRunner.__new__(BaseJobRunner)
    runner.app = cast(
        "GalaxyManagerApplication",
        SimpleNamespace(container_finder=SimpleNamespace(find_container=lambda *args: None), object_store=None),
    )
    return runner


def test_user_defined_tools_always_require_container():
    assert _job_wrapper(tool_type="user_defined").requires_containerization
    assert not _job_wrapper().requires_containerization
    assert _job_wrapper(require_container="True").requires_containerization


@pytest.mark.parametrize(
    "compute_directories",
    [
        {},
        # Pulsar resolves containers for its remote job directory and builds its own command line.
        {
            "compute_working_directory": "/pulsar/1/working",
            "compute_job_directory": "/pulsar/1",
        },
    ],
)
def test_find_container_enforces_require_container(compute_directories, monkeypatch):
    monkeypatch.setattr("galaxy.jobs.runners.get_disk_paths", lambda object_store: set())
    runner = _runner_without_containers()
    assert runner._find_container(_job_wrapper(), **compute_directories) is None
    with pytest.raises(Exception, match="Failed to find a container when required"):
        runner._find_container(_job_wrapper(tool_type="user_defined"), **compute_directories)
    with pytest.raises(Exception, match="Failed to find a container when required"):
        runner._find_container(_job_wrapper(require_container="True"), **compute_directories)
