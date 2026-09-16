import shlex
import subprocess
from inspect import signature

import pytest

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

    assert "$(id -u -- alice)" in command
    assert '--user "$GALAXY_DOCKER_UID:$GALAXY_DOCKER_GID"' in command


def test_docker_run_command_prefers_explicit_set_user():
    command = docker_util.build_docker_run_command(
        "echo hello",
        "busybox",
        set_user="1000:1000",
        set_user_from_host=False,
    )

    assert "--user 1000:1000" in command
    assert "id -u alice" not in command


def test_docker_run_command_preserves_existing_positional_parameters():
    parameters = list(signature(docker_util.build_docker_run_command).parameters)
    assert parameters[parameters.index("set_user") + 1 : parameters.index("set_user_from_host")] == [
        "host",
        "guest_ports",
        "host_port_cmd",
        "container_name",
    ]


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
    assert "$(id -G -- alice)" in command
    assert "$GALAXY_DOCKER_GROUP_ARGS" in command
    assert '--user "$GALAXY_DOCKER_UID:$GALAXY_DOCKER_GID"' in command


def test_docker_container_oidc_user_overrides_implicit_default_user():
    container = _docker_container(
        {
            "docker_volumes": "$working_directory:rw",
            "docker_username_from_token": "alice",
            "docker_username_from_oidc_token_claim": {"set_user": True},
        }
    )

    command = container.containerize_command("echo hello")

    assert '--user "$GALAXY_DOCKER_UID:$GALAXY_DOCKER_GID"' in command
    assert "$(id -G -- alice)" in command
    assert "$GALAXY_DOCKER_GROUP_ARGS" in command


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


@pytest.mark.parametrize("set_user", [False, "false", "False", "0"])
def test_env_only_boolean_never_resolves_host_identity(set_user):
    container = _docker_container(
        {
            "docker_set_user": "1000:1000",
            "docker_username_from_token": "alice",
            "docker_username_from_oidc_token_claim": {"set_user": set_user, "expose_as_env": "GALAXY_TOOL_USER"},
        }
    )
    result = _execute(container.containerize_command("echo hello"), 'echo "Unexpected identity lookup" >&2; return 1')
    assert result.returncode == 0, result.stderr
    arguments = result.stdout.splitlines()
    assert arguments[arguments.index("--user") + 1] == "1000:1000"
    assert "--group-add" not in arguments
    assert "GALAXY_TOOL_USER=alice" in arguments


def _execute(
    command, id_body='case "$1" in -u) echo 1234;; -g) echo 2345;; -G) echo "2345 3456";; esac', shell="/bin/sh"
):
    script = f"""id() {{ {id_body}; }}
docker() {{
    printf 'DOCKER_CALL\\n'
    if [ "$1" = run ]; then
        printf 'DOCKER_RUN\\n'
        printf '%s\\n' "$@"
    fi
}}
{command}
"""
    return subprocess.run([shell, "-c", script], capture_output=True, text=True)


@pytest.mark.parametrize("shell", ["/bin/sh", "/bin/bash"])
@pytest.mark.parametrize(
    "identity", ["alice smith", "$(printf TOKEN_EXPANDED)", "`printf TOKEN_EXPANDED`", "a'b\"c;$HOME"]
)
@pytest.mark.parametrize("set_user", [False, True])
def test_token_identity_is_literal_shell_data(identity, set_user, shell):
    container = _docker_container(
        {
            "docker_volumes": "$working_directory:rw",
            "docker_set_user": None,
            "docker_username_from_token": identity,
            "docker_username_from_oidc_token_claim": {"set_user": set_user, "expose_as_env": "GALAXY_TOOL_USER"},
        }
    )
    # Verify the id argument too: quoting only the Docker environment is insufficient.
    id_body = f"""[ "$2" = -- ] && [ "$3" = {shlex.quote(identity)} ] || return 1
case "$1" in -u) echo 1234;; -g) echo 2345;; -G) echo "2345 3456";; esac"""
    result = _execute(container.containerize_command("echo hello"), id_body, shell)
    assert result.returncode == 0, result.stderr
    arguments = result.stdout.splitlines()
    assert f"GALAXY_TOOL_USER={identity}" in arguments
    if set_user:
        assert arguments[arguments.index("--user") + 1] == "1234:2345"
        assert arguments.count("--group-add") == 2
        assert "3456" in arguments
    else:
        assert "--user" not in arguments
        assert "--group-add" not in arguments


@pytest.mark.parametrize("lookup", ["-u", "-g", "-G"])
@pytest.mark.parametrize("output", [None, "", " ", "not-numeric", "1234:0", "*", "1234\n5678", "1234\t5678"])
def test_host_identity_lookup_fails_closed(lookup, output):
    container = _docker_container(
        {
            "docker_username_from_token": "alice",
            "docker_username_from_oidc_token_claim": {"set_user": True},
        }
    )
    failure = "return 1" if output is None else f"printf '%s\\n' {shlex.quote(output)}; return 0"
    result = _execute(
        container.containerize_command("echo hello"),
        f'if [ "$1" = {shlex.quote(lookup)} ]; then {failure}; fi; '
        'case "$1" in -u) echo 1234;; -g) echo 2345;; -G) echo "2345 3456";; esac',
    )
    assert result.returncode != 0
    assert "DOCKER_CALL" not in result.stdout
    assert "Docker" in result.stderr


def test_direct_docker_host_identity_lookup_fails_closed():
    command = docker_util.build_docker_run_command("echo hello", "busybox", set_user="alice", set_user_from_host=True)
    result = _execute(command, "return 1")
    assert result.returncode != 0
    assert "DOCKER_CALL" not in result.stdout


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
