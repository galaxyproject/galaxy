import re
from types import SimpleNamespace
from typing import (
    cast,
    TYPE_CHECKING,
)

import pytest

from galaxy.jobs.runners import BaseJobRunner
from galaxy.jobs.runners.pulsar import PulsarComputeEnvironment
from galaxy.tool_util.deps.container_classes import (
    DockerContainer,
    SingularityContainer,
)
from galaxy.tool_util.deps.dependencies import AppInfo

if TYPE_CHECKING:
    from galaxy.app import GalaxyManagerApplication

LOCAL_SHARED_HOME = "/galaxy/shared_home"
REMOTE_SHARED_HOME = "/pulsar/shared_home"
APP_INFO = AppInfo(galaxy_root_dir="/galaxy", container_image_cache_path="/galaxy/container_cache")
PULSAR_DIRECTORIES = {
    "compute_working_directory": "/pulsar/staging/1/working",
    "compute_job_directory": "/pulsar/staging/1",
}


def _job_wrapper(home_target, environment_variables=(), tool_env_names=()):
    destination_params = {"shared_home_dir": LOCAL_SHARED_HOME}
    local_homes = {None: None, "shared_home": LOCAL_SHARED_HOME, "job_home": "$_GALAXY_JOB_HOME_DIR"}
    tool = SimpleNamespace(
        containers=[],
        requirements=[],
        requires_galaxy_python_environment=False,
        docker_env_pass_through=["GALAXY_SLOTS", "HOME", "_GALAXY_JOB_HOME_DIR", "_GALAXY_JOB_TMP_DIR"],
        environment_variables=[{"name": name} for name in environment_variables],
        id="cat",
        version="1.0",
        profile=24.0,
        tool_dir="/tools/cat",
    )
    return SimpleNamespace(
        tool=tool,
        home_target=home_target,
        tmp_target=None,
        guest_ports=None,
        working_directory="/galaxy/jobs/1",
        tool_working_directory="/galaxy/jobs/1/working",
        tmp_directory=lambda: None,
        home_directory=lambda: local_homes[home_target],
        job_destination=SimpleNamespace(params=destination_params, tool_env_names=list(tool_env_names)),
        set_container=lambda container: None,
    )


def _pulsar_compute_environment(job_wrapper, remote_job_config):
    compute_environment = PulsarComputeEnvironment.__new__(PulsarComputeEnvironment)
    compute_environment.job_wrapper = job_wrapper
    compute_environment._working_directory = remote_job_config["working_directory"]
    compute_environment._tmp_dir = remote_job_config.get("tmp_dir")
    compute_environment._shared_home_dir = remote_job_config.get("shared_home_dir")
    return compute_environment


def _runner(container_class=SingularityContainer):
    def find_container(tool_info, destination_info, job_info):
        return container_class("busybox", APP_INFO, tool_info, destination_info, job_info, None)

    runner = BaseJobRunner.__new__(BaseJobRunner)
    runner.app = cast(
        "GalaxyManagerApplication",
        SimpleNamespace(container_finder=SimpleNamespace(find_container=find_container), object_store=None),
    )
    return runner


@pytest.fixture(autouse=True)
def _no_disk_paths(monkeypatch):
    monkeypatch.setattr("galaxy.jobs.runners.get_disk_paths", lambda object_store: set())


def test_pulsar_container_without_compute_home_does_not_mount_home():
    # The Pulsar server has no shared_home_dir, so its job script does not set HOME.
    job_wrapper = _job_wrapper("shared_home")
    compute_environment = _pulsar_compute_environment(job_wrapper, {"working_directory": "/pulsar/staging/1/working"})
    container = _runner()._find_container(job_wrapper, **PULSAR_DIRECTORIES, compute_environment=compute_environment)
    assert container.job_info.home_directory is None
    command = container.containerize_command("true")
    assert "--home" not in command
    assert LOCAL_SHARED_HOME not in command


def test_pulsar_container_uses_compute_home():
    job_wrapper = _job_wrapper("shared_home")
    compute_environment = _pulsar_compute_environment(
        job_wrapper,
        {"working_directory": "/pulsar/staging/1/working", "shared_home_dir": REMOTE_SHARED_HOME},
    )
    container = _runner()._find_container(job_wrapper, **PULSAR_DIRECTORIES, compute_environment=compute_environment)
    command = container.containerize_command("true")
    assert f'--home "{REMOTE_SHARED_HOME}:{REMOTE_SHARED_HOME}"' in command
    assert LOCAL_SHARED_HOME not in command


@pytest.mark.parametrize("home_target", ["job_home", "shared_home"])
def test_local_container_uses_job_wrapper_home(home_target):
    job_wrapper = _job_wrapper(home_target)
    home = job_wrapper.home_directory()
    command = _runner()._find_container(job_wrapper).containerize_command("true")
    assert f'--home "{home}:{home}"' in command


def test_container_without_home_does_not_mount_home():
    command = _runner()._find_container(_job_wrapper(None)).containerize_command("true")
    assert "--home" not in command


@pytest.mark.parametrize(
    "job_wrapper_kwds",
    [{"environment_variables": ["HOME"]}, {"tool_env_names": ["HOME"]}],
)
def test_container_uses_home_exported_by_tool_or_destination(job_wrapper_kwds):
    command = _runner()._find_container(_job_wrapper(None, **job_wrapper_kwds)).containerize_command("true")
    assert '--home "$HOME:$HOME"' in command


@pytest.mark.parametrize(
    "job_wrapper_kwds",
    [{"environment_variables": ["HOME"]}, {"tool_env_names": ["HOME"]}],
)
def test_docker_volumes_ignore_home_exported_by_tool_or_destination(job_wrapper_kwds):
    def volumes(job_wrapper):
        command = _runner(DockerContainer)._find_container(job_wrapper).containerize_command("true")
        return re.findall(r"-v (\S+)", command)

    assert volumes(_job_wrapper(None, **job_wrapper_kwds)) == volumes(_job_wrapper(None))
