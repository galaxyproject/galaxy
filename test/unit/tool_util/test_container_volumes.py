import pytest

from galaxy.tool_util.deps.container_classes import (
    DockerContainer,
    SingularityContainer,
)
from galaxy.tool_util.deps.dependencies import (
    AppInfo,
    JobInfo,
    ToolInfo,
)


def _container(container_class, tool_directory):
    job_info = JobInfo(
        working_directory="/jobs/1/working",
        tool_directory=tool_directory,
        job_directory="/jobs/1",
        tmp_directory=None,
        home_directory=None,
        job_directory_type="galaxy",
    )
    return container_class("busybox", AppInfo(), ToolInfo(profile=24.0), {}, job_info, None)


@pytest.mark.parametrize("container_class", [DockerContainer, SingularityContainer])
@pytest.mark.parametrize(
    "volumes_str",
    [
        "$tool_directory:ro,$working_directory:rw,$job_directory:rw",
        "$working_directory:rw,$tool_directory:ro,$job_directory:rw",
        "$working_directory:rw,$job_directory:rw,$tool_directory:ro",
    ],
)
def test_tool_directory_stripped_without_tool_directory(container_class, volumes_str):
    container = _container(container_class, tool_directory=None)
    expanded = container._expand_volume_str(volumes_str)
    assert "$tool_directory" not in expanded
    assert [v for v in expanded.split(",") if v] == ["/jobs/1/working:rw", "/jobs/1:rw"]


@pytest.mark.parametrize("container_class", [DockerContainer, SingularityContainer])
def test_tool_directory_kept_with_tool_directory(container_class):
    container = _container(container_class, tool_directory="/tools/cat")
    expanded = container._expand_volume_str("$tool_directory:ro,$working_directory:rw")
    assert expanded == "/tools/cat:ro,/jobs/1/working:rw"
