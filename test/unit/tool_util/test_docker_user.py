from galaxy.tool_util.deps import docker_util
from galaxy.tool_util.deps.container_classes import DockerContainer
from galaxy.tool_util.deps.dependencies import (
    AppInfo,
    JobInfo,
    ToolInfo,
)


def test_docker_run_command_can_set_user_from_host():
    command = docker_util.build_docker_run_command(
        "echo hello",
        "busybox",
        set_user="alice",
        set_user_from_host=True,
    )

    assert "--user `id -u alice`:`id -g alice`" in command


def test_docker_run_command_prefers_explicit_set_user():
    command = docker_util.build_docker_run_command(
        "echo hello",
        "busybox",
        set_user="1000:1000",
        set_user_from_host=False,
    )

    assert "--user 1000:1000" in command
    assert "id -u alice" not in command


def test_docker_container_passes_docker_username_from_token_env_and_groups():
    container = _docker_container(
        {
            "docker_volumes": "$working_directory:rw",
            "docker_set_user": None,
            "docker_username_from_token": "alice",
            "docker_username_from_oidc_token_claim": {"set_user": True, "expose_as_env": "GALAXY_TOOL_USER"},
        }
    )

    command = container.containerize_command("echo hello")

    assert "-e GALAXY_TOOL_USER=alice" in command
    assert "USERGROUPS=`id -G alice`" in command
    assert "$GROUPADD" in command
    assert "--user `id -u alice`:`id -g alice`" in command


def test_docker_container_oidc_user_overrides_implicit_default_user():
    container = _docker_container(
        {
            "docker_volumes": "$working_directory:rw",
            "docker_username_from_token": "alice",
            "docker_username_from_oidc_token_claim": {"set_user": True},
        }
    )

    command = container.containerize_command("echo hello")

    assert "--user `id -u alice`:`id -g alice`" in command
    assert "USERGROUPS=`id -G alice`" in command
    assert "$GROUPADD" in command


def test_docker_container_can_expose_token_username_without_setting_user():
    container = _docker_container(
        {
            "docker_volumes": "$working_directory:rw",
            "docker_username_from_token": "alice",
            "docker_username_from_oidc_token_claim": {"expose_as_env": "GALAXY_TOOL_USER"},
            "docker_set_user": None,
        }
    )

    command = container.containerize_command("echo hello")

    assert "-e GALAXY_TOOL_USER=alice" in command
    assert "USERGROUPS=`id -G alice`" not in command
    assert "$GROUPADD" not in command
    assert "--user `id -u alice`:`id -g alice`" not in command


def _docker_container(destination_info):
    return DockerContainer(
        "busybox",
        AppInfo(
            galaxy_root_dir="/galaxy",
            default_file_path="/data",
            container_image_cache_path="/tmp/galaxy-test-container-cache",
        ),
        ToolInfo(env_pass_through=[], profile=24.0),
        destination_info,
        JobInfo(
            working_directory="/job/working",
            tool_directory=None,
            job_directory="/job",
            tmp_directory=None,
            home_directory=None,
            job_directory_type="galaxy",
        ),
        None,
        container_name="test-container",
    )
