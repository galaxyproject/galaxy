from types import SimpleNamespace
from typing import (
    cast,
    TYPE_CHECKING,
)

import pytest

from galaxy.jobs.runners import (
    BaseJobRunner,
    ContainerNotAllowedError,
)
from galaxy.tool_util.deps.image_references import ContainerAllowlist
from galaxy.tool_util.deps.requirements import ContainerDescription

if TYPE_CHECKING:
    from galaxy.app import GalaxyManagerApplication
    from galaxy.jobs import MinimalJobWrapper

RESOLVED = object()


def _job_wrapper(identifier: str, tool_type: str = "user_defined"):
    tool = SimpleNamespace(
        tool_type=tool_type,
        containers=[ContainerDescription(identifier)],
        requirements=[],
        requires_galaxy_python_environment=False,
        docker_env_pass_through=[],
        id="cat",
        version="1.0",
        profile=24.0,
        tool_dir="/tools/cat",
    )
    job_wrapper = SimpleNamespace(
        tool=tool,
        guest_ports=None,
        working_directory="/jobs/000/1",
        tool_working_directory="/jobs/000/1/working",
        tmp_directory=lambda: None,
        home_directory=lambda: None,
        job_destination=SimpleNamespace(params={}, tool_env_names=[]),
        set_container=lambda container: None,
    )
    return cast("MinimalJobWrapper", job_wrapper)


def _runner():
    runner = BaseJobRunner.__new__(BaseJobRunner)
    runner.app = cast(
        "GalaxyManagerApplication",
        SimpleNamespace(
            # Resolvers may map the declared image to anything, e.g. a cached Singularity image path.
            container_finder=SimpleNamespace(find_container=lambda *args: RESOLVED),
            dynamic_tool_manager=SimpleNamespace(container_allowlist=ContainerAllowlist(["quay.io/biocontainers/*"])),
            object_store=None,
        ),
    )
    return runner


@pytest.fixture(autouse=True)
def no_disk_paths(monkeypatch):
    monkeypatch.setattr("galaxy.jobs.runners.get_disk_paths", lambda object_store: set())


def test_user_defined_tool_with_disallowed_container_fails():
    with pytest.raises(ContainerNotAllowedError, match="Container 'busybox' is not allowed"):
        _runner()._find_container(_job_wrapper("busybox"))


def test_user_defined_tool_with_allowed_container_proceeds():
    assert _runner()._find_container(_job_wrapper("quay.io/biocontainers/samtools:1.17")) is RESOLVED


def test_other_tools_are_not_checked():
    assert _runner()._find_container(_job_wrapper("busybox", tool_type="default")) is RESOLVED
