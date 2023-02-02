import os
import shlex

DEFAULT_WORKING_DIRECTORY = None
DEFAULT_SINGULARITY_COMMAND = "singularity"
DEFAULT_CLEANENV = True
DEFAULT_SUDO = False
DEFAULT_SUDO_COMMAND = "sudo"
DEFAULT_RUN_EXTRA_ARGUMENTS = None


def pull_mulled_singularity_command(
    docker_image_identifier,
    cache_directory,
    namespace=None,
    singularity_cmd=DEFAULT_SINGULARITY_COMMAND,
    sudo=DEFAULT_SUDO,
    sudo_cmd=DEFAULT_SUDO_COMMAND,
):
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
):
    # Make sure cache dir exists
    dirname = os.path.dirname(os.path.normpath(cache_path))
    os.makedirs(dirname, exist_ok=True)
    command_parts = _singularity_prefix(singularity_cmd, sudo, sudo_cmd)
    command_parts.extend(["build", cache_path, image_identifier])
    return command_parts


def build_singularity_run_command(
    container_command,
    image,
    volumes=None,
    env=None,
    working_directory=DEFAULT_WORKING_DIRECTORY,
    singularity_cmd=DEFAULT_SINGULARITY_COMMAND,
    run_extra_arguments=DEFAULT_RUN_EXTRA_ARGUMENTS,
    sudo=DEFAULT_SUDO,
    sudo_cmd=DEFAULT_SUDO_COMMAND,
    guest_ports=False,
    container_name=None,
    cleanenv=DEFAULT_CLEANENV,
):
    volumes = volumes or []
    env = env or []
    command_parts = []
    # http://singularity.lbl.gov/docs-environment-metadata
    home = None
    for key, value in env:
        if key == "HOME":
            home = value
        command_parts.extend([f"SINGULARITYENV_{key}={value}"])
    command_parts += _singularity_prefix(
        singularity_cmd=singularity_cmd,
        sudo=sudo,
        sudo_cmd=sudo_cmd,
    )
    command_parts.append("-s")
    command_parts.append("exec")
    if cleanenv:
        command_parts.append("--cleanenv")
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
    singularity_cmd=DEFAULT_SINGULARITY_COMMAND, sudo=DEFAULT_SUDO, sudo_cmd=DEFAULT_SUDO_COMMAND, **kwds
):
    """Prefix to issue a singularity command."""
    command_parts = []
    if sudo:
        command_parts.append(sudo_cmd)
    command_parts.append(singularity_cmd)
    return command_parts


__all__ = ("build_singularity_run_command", "pull_mulled_singularity_command", "pull_singularity_command")
