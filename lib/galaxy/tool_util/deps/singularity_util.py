import os
import shlex
from typing import (
    List,
    Optional,
    Tuple,
    TYPE_CHECKING,
    Union,
)

if TYPE_CHECKING:
    from .container_volumes import DockerVolume

DEFAULT_WORKING_DIRECTORY = None
DEFAULT_SINGULARITY_COMMAND = "singularity"
DEFAULT_CLEANENV = True
DEFAULT_NO_MOUNT = ["tmp"]
DEFAULT_SUDO = False
DEFAULT_SUDO_COMMAND = "sudo"
DEFAULT_RUN_EXTRA_ARGUMENTS = None


def pull_mulled_singularity_command(
    docker_image_identifier: str,
    cache_directory: str,
    namespace: Optional[str] = None,
    singularity_cmd: str = DEFAULT_SINGULARITY_COMMAND,
    sudo: bool = DEFAULT_SUDO,
    sudo_cmd: str = DEFAULT_SUDO_COMMAND,
) -> List[str]:
    command_parts = []
    command_parts += _singularity_prefix(
        singularity_cmd=singularity_cmd,
        sudo=sudo,
        sudo_cmd=sudo_cmd,
    )
    save_path = docker_image_identifier
    if namespace:
        prefix = f"docker://quay.io/{namespace}/"
        if docker_image_identifier.startswith(prefix):
            save_path = docker_image_identifier[len(prefix) :]
    command_parts.extend(["build", os.path.join(cache_directory, save_path), docker_image_identifier])
    return command_parts


def pull_singularity_command(
    image_identifier: str,
    cache_path: str,
    singularity_cmd: str = DEFAULT_SINGULARITY_COMMAND,
    sudo: bool = DEFAULT_SUDO,
    sudo_cmd: str = DEFAULT_SUDO_COMMAND,
) -> List[str]:
    # Make sure cache dir exists
    dirname = os.path.dirname(os.path.normpath(cache_path))
    os.makedirs(dirname, exist_ok=True)
    command_parts = _singularity_prefix(singularity_cmd, sudo, sudo_cmd)
    command_parts.extend(["build", cache_path, image_identifier])
    return command_parts


def build_singularity_run_command(
    container_command: str,
    image: str,
    volumes: Optional[List["DockerVolume"]] = None,
    env: Optional[List[Tuple[str, str]]] = None,
    working_directory: Optional[str] = DEFAULT_WORKING_DIRECTORY,
    singularity_cmd: str = DEFAULT_SINGULARITY_COMMAND,
    run_extra_arguments: Optional[str] = DEFAULT_RUN_EXTRA_ARGUMENTS,
    sudo: bool = DEFAULT_SUDO,
    sudo_cmd: str = DEFAULT_SUDO_COMMAND,
    guest_ports: Union[bool, List[str]] = False,
    container_name: Optional[str] = None,
    cleanenv: bool = DEFAULT_CLEANENV,
    no_mount: Optional[List[str]] = DEFAULT_NO_MOUNT,
) -> str:
    volumes = volumes or []
    env = env or []
    command_parts = []
    # http://singularity.lbl.gov/docs-environment-metadata
    home = None
    for key, value in env:
        if key == "HOME":
            home = value
        command_parts.extend([f'SINGULARITYENV_{key}="{value}"'])
    command_parts += _singularity_prefix(
        singularity_cmd=singularity_cmd,
        sudo=sudo,
        sudo_cmd=sudo_cmd,
    )
    command_parts.append("-s")
    command_parts.append("exec")
    if cleanenv:
        command_parts.append("--cleanenv")
    if no_mount:
        command_parts.extend(["--no-mount", ",".join(no_mount)])
    for volume in volumes:
        command_parts.extend(["-B", str(volume)])
    if home is not None:
        command_parts.extend(["--home", f"{home}:{home}"])
    if run_extra_arguments:
        command_parts.append(run_extra_arguments)
    full_image = image
    command_parts.append(shlex.quote(full_image))
    command_parts.append(container_command)
    return " ".join(command_parts)


def _singularity_prefix(
    singularity_cmd: str = DEFAULT_SINGULARITY_COMMAND,
    sudo: bool = DEFAULT_SUDO,
    sudo_cmd: str = DEFAULT_SUDO_COMMAND,
    **kwds,
) -> List[str]:
    """Prefix to issue a singularity command."""
    command_parts = []
    if sudo:
        command_parts.append(sudo_cmd)
    command_parts.append(singularity_cmd)
    return command_parts


__all__ = ("build_singularity_run_command", "pull_mulled_singularity_command", "pull_singularity_command")
