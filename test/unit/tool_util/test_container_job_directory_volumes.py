import shlex

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

JOB_DIRECTORY = "/jobs/000/1"
WORKING_DIRECTORY = f"{JOB_DIRECTORY}/working"


def _container(container_class, job_directory_type, destination_info=None, profile=24.0, job_type="tool"):
    job_info = JobInfo(
        working_directory=WORKING_DIRECTORY,
        tool_directory="/tools/cat",
        job_directory=JOB_DIRECTORY,
        tmp_directory=None,
        home_directory=None,
        job_directory_type=job_directory_type,
        job_type=job_type,
        output_paths=set(),
    )
    return container_class(
        "busybox:latest",
        AppInfo(
            galaxy_root_dir="/galaxy",
            default_file_path="/data/objects",
            container_image_cache_path="/cache",
        ),
        ToolInfo(profile=profile),
        destination_info or {},
        job_info,
        None,
    )


def _volumes(command):
    """Map volume source to its full spec for the -v (docker) / -B (singularity) arguments."""
    tokens = shlex.split(command)
    return {
        tokens[i + 1].split(":", 1)[0]: tokens[i + 1] for i, token in enumerate(tokens[:-1]) if token in ("-v", "-B")
    }


@pytest.mark.parametrize("container_class", [DockerContainer, SingularityContainer])
@pytest.mark.parametrize("job_directory_type", ["galaxy", "pulsar"])
def test_default_volumes_do_not_expose_job_directory(container_class, job_directory_type):
    command = _container(container_class, job_directory_type).containerize_command("bash tool_script.sh")
    sources = _volumes(command)
    assert JOB_DIRECTORY not in sources
    assert f"{JOB_DIRECTORY}/tool_script.sh" in sources
    assert f"{JOB_DIRECTORY}/inputs" in sources
    assert f"{JOB_DIRECTORY}/configs" in sources
    assert f"{JOB_DIRECTORY}/outputs" in sources
    assert WORKING_DIRECTORY in sources
    assert f"{JOB_DIRECTORY}/metadata" not in sources
    if job_directory_type == "pulsar":
        assert f"{JOB_DIRECTORY}/unstructured" in sources
        # Mount sources must exist before the container starts, Pulsar creates this one lazily.
        assert f'mkdir -p "{JOB_DIRECTORY}/unstructured"' in command
    else:
        # Galaxy creates the mounted subdirectories with the job directory.
        assert "mkdir -p" not in command


@pytest.mark.parametrize("container_class", [DockerContainer, SingularityContainer])
def test_job_directory_tool_script_mounted_read_only(container_class):
    command = _container(container_class, "pulsar").containerize_command("bash tool_script.sh")
    volumes = _volumes(command)
    assert volumes[f"{JOB_DIRECTORY}/tool_script.sh"].endswith(":ro")
    assert volumes[f"{JOB_DIRECTORY}/inputs"].endswith(":ro")
    assert volumes[f"{JOB_DIRECTORY}/configs"].endswith(":ro")


@pytest.mark.parametrize("container_class", [DockerContainer, SingularityContainer])
def test_legacy_profile_configs_writable(container_class):
    command = _container(container_class, "galaxy", profile=19.09).containerize_command("bash tool_script.sh")
    # singularity binds are writable unless marked ro
    assert not _volumes(command)[f"{JOB_DIRECTORY}/configs"].endswith(":ro")


@pytest.mark.parametrize("container_class", [DockerContainer, SingularityContainer])
def test_defaults_extendable(container_class):
    key = f"{container_class.container_type}_volumes"
    container = _container(container_class, "pulsar", destination_info={key: "$defaults,/refdata:ro"})
    sources = _volumes(container.containerize_command("bash tool_script.sh"))
    assert "/refdata" in sources
    assert JOB_DIRECTORY not in sources


@pytest.mark.parametrize("container_class", [DockerContainer, SingularityContainer])
@pytest.mark.parametrize("job_directory_type", ["galaxy", "pulsar"])
def test_epilog_containers_keep_job_directory(container_class, job_directory_type):
    # Containerized metadata runs Galaxy's own code against the whole job directory.
    command = _container(container_class, job_directory_type, job_type="epilog").containerize_command("set_metadata")
    assert JOB_DIRECTORY in _volumes(command)
    assert "mkdir -p" not in command
