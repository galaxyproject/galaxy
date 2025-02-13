"""Utilities for building up Docker commands...

...using common defaults and configuration mechanisms.
"""

import os
import shlex
import sys
from typing import (
    List,
    Optional,
    TYPE_CHECKING,
    Union,
)

if TYPE_CHECKING:
    from .container_volumes import DockerVolume

from galaxy.util.commands import argv_to_str

DEFAULT_DOCKER_COMMAND = "docker"
DEFAULT_SUDO = False
DEFAULT_SUDO_COMMAND = "sudo"
DEFAULT_HOST = None
DEFAULT_VOLUME_MOUNT_TYPE = "rw"
DEFAULT_WORKING_DIRECTORY = None
DEFAULT_NET = None
DEFAULT_MEMORY = None
DEFAULT_VOLUMES_FROM = None
DEFAULT_AUTO_REMOVE = True
DEFAULT_SET_USER = None if sys.platform == "darwin" else "$UID"
DEFAULT_RUN_EXTRA_ARGUMENTS = None


def kill_command(container: str, signal: Optional[str] = None, **kwds) -> List[str]:
    args = (["-s", signal] if signal else []) + [container]
    return command_list("kill", args, **kwds)


def logs_command(container: str, **kwds) -> List[str]:
    return command_list("logs", [container], **kwds)


def build_command(image: str, docker_build_path: str, **kwds) -> List[str]:
    if os.path.isfile(docker_build_path):
        docker_build_path = os.path.dirname(os.path.abspath(docker_build_path))
    return command_list("build", ["-t", image, docker_build_path], **kwds)


def build_save_image_command(image: str, destination: str, **kwds) -> List[str]:
    return command_list("save", ["-o", destination, image], **kwds)


def build_pull_command(tag: str, **kwds) -> List[str]:
    return command_list("pull", [tag], **kwds)


def build_docker_cache_command(image: str, **kwds) -> str:
    assert kwds.get("to_str", True)
    inspect_image_command = command_shell("inspect", [image], **kwds)
    pull_image_command = command_shell("pull", [image], **kwds)
    cache_command = f"{inspect_image_command} > /dev/null 2>&1\n[ $? -ne 0 ] && {pull_image_command} > /dev/null 2>&1\n"
    return cache_command


def build_docker_images_command(truncate=True, **kwds) -> Union[str, List[str]]:
    args = ["--no-trunc"] if not truncate else []
    return command_shell("images", args, **kwds)


def build_docker_load_command(**kwds) -> Union[str, List[str]]:
    return command_shell("load", [])


def build_docker_simple_command(
    command: str,
    docker_cmd: str = DEFAULT_DOCKER_COMMAND,
    sudo: bool = DEFAULT_SUDO,
    sudo_cmd: str = DEFAULT_SUDO_COMMAND,
    container_name: Optional[str] = None,
    **kwd,
) -> str:
    command_parts = _docker_prefix(
        docker_cmd=docker_cmd,
        sudo=sudo,
        sudo_cmd=sudo_cmd,
    )
    command_parts.append(command)
    command_parts.append(container_name or "{CONTAINER_NAME}")
    return " ".join(command_parts)


def build_docker_run_command(
    container_command: str,
    image: str,
    interactive: bool = False,
    terminal: bool = False,
    tag: Optional[str] = None,
    volumes: Optional[List["DockerVolume"]] = None,
    volumes_from: Optional[str] = DEFAULT_VOLUMES_FROM,
    memory: Optional[str] = DEFAULT_MEMORY,
    env_directives: Optional[List[str]] = None,
    working_directory: Optional[str] = DEFAULT_WORKING_DIRECTORY,
    name: Optional[str] = None,
    net: Optional[str] = DEFAULT_NET,
    run_extra_arguments: Optional[str] = DEFAULT_RUN_EXTRA_ARGUMENTS,
    docker_cmd: str = DEFAULT_DOCKER_COMMAND,
    sudo: bool = DEFAULT_SUDO,
    sudo_cmd: str = DEFAULT_SUDO_COMMAND,
    auto_rm: bool = DEFAULT_AUTO_REMOVE,
    set_user: Optional[str] = DEFAULT_SET_USER,
    host: Optional[str] = DEFAULT_HOST,
    guest_ports: Union[bool, str, List[str]] = False,
    container_name: Optional[str] = None,
) -> str:
    env_directives = env_directives or []
    volumes = volumes or []
    command_parts = _docker_prefix(docker_cmd=docker_cmd, sudo=sudo, sudo_cmd=sudo_cmd, host=host)
    command_parts.append("run")
    if interactive:
        command_parts.append("-i")
    if terminal:
        command_parts.append("-t")
    for env_directive in env_directives:
        # e.g. -e "GALAXY_SLOTS=$GALAXY_SLOTS"
        # These are environment variable expansions so we don't quote these.
        command_parts.extend(["-e", env_directive])
    if guest_ports is True:
        # When is True, expose all ports
        command_parts.append("-P")
    elif guest_ports:
        if not isinstance(guest_ports, list):
            guest_ports = [guest_ports]
        for guest_port in guest_ports:
            command_parts.extend(["-p", guest_port])
    if container_name:
        command_parts.extend(["--name", container_name])
    for volume in volumes:
        command_parts.extend(["-v", str(volume)])
    if volumes_from:
        command_parts.extend(["--volumes-from", shlex.quote(str(volumes_from))])
    if memory:
        command_parts.extend(["-m", shlex.quote(memory)])
    command_parts.extend(["--cpus", "${GALAXY_SLOTS:-1}"])
    if name:
        command_parts.extend(["--name", shlex.quote(name)])
    if working_directory:
        command_parts.extend(["-w", shlex.quote(working_directory)])
    if net:
        command_parts.extend(["--net", shlex.quote(net)])
    if auto_rm:
        command_parts.append("--rm")
    if run_extra_arguments:
        command_parts.append(run_extra_arguments)
    if set_user:
        user = set_user
        if set_user == DEFAULT_SET_USER:
            # If future-us is ever in here and fixing this for docker-machine just
            # use cwltool.docker_id - it takes care of this default nicely.
            euid = os.geteuid()
            egid = os.getgid()

            user = f"{euid}:{egid}"
        command_parts.extend(["--user", user])
    full_image = image
    if tag:
        full_image = f"{full_image}:{tag}"
    command_parts.append(shlex.quote(full_image))
    command_parts.append(container_command)
    return " ".join(command_parts)


def command_list(command: str, command_args: Optional[List[str]] = None, **kwds) -> List[str]:
    """Return Docker command as an argv list."""
    command_args = command_args or []
    command_parts = _docker_prefix(**kwds)
    command_parts.append(command)
    command_parts.extend(command_args)
    return command_parts


def command_shell(command: str, command_args: Optional[List[str]] = None, **kwds) -> Union[str, List[str]]:
    """Return Docker command as a string for a shell or command-list."""
    command_args = command_args or []
    cmd = command_list(command, command_args, **kwds)
    to_str = kwds.get("to_str", True)
    if to_str:
        return argv_to_str(cmd)
    else:
        return cmd


def _docker_prefix(
    docker_cmd: str = DEFAULT_DOCKER_COMMAND,
    sudo: bool = DEFAULT_SUDO,
    sudo_cmd: str = DEFAULT_SUDO_COMMAND,
    host: Optional[str] = DEFAULT_HOST,
    **kwds,
) -> List[str]:
    """Prefix to issue a docker command."""
    command_parts = []
    if sudo:
        command_parts.append(sudo_cmd)
    command_parts.extend(docker_cmd.split())
    if host:
        command_parts.extend(["-H", host])
    return command_parts


def parse_port_text(port_text):
    """

    >>> slurm_ports = parse_port_text("8888/tcp -> 0.0.0.0:32769")
    >>> slurm_ports[8888]['host']
    '0.0.0.0'
    >>> ports = parse_port_text("5432/tcp -> :::5432")
    >>> len(ports)
    0
    >>> ports_new = parse_port_text("5432/tcp -> [::]:5432")
    >>> len(ports_new)
    0
    """
    ports = None
    if port_text is not None:
        ports = {}
        for line in port_text.strip().split("\n"):
            if " -> " not in line:
                raise Exception(f"Cannot parse host and port from line [{line}]")
            tool, host = line.split(" -> ", 1)
            hostname, port = host.rsplit(":", 1)
            if hostname in ["::", "[::]"]:
                # Skip unspecified IPv6 address, which is also specified as 0:0:0:0 in another line.
                # This is brittle of course, but so is parsing the container ports like this.
                continue
            port = int(port)
            tool_p, tool_prot = tool.split("/")
            tool_p = int(tool_p)
            ports[tool_p] = dict(tool_port=tool_p, host=hostname, port=port, protocol=tool_prot)
    return ports
