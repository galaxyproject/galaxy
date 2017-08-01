from six.moves import shlex_quote


DEFAULT_WORKING_DIRECTORY = None
DEFAULT_SINGULARITY_COMMAND = "singularity"
DEFAULT_SUDO = False
DEFAULT_SUDO_COMMAND = "sudo"
DEFAULT_RUN_EXTRA_ARGUMENTS = None


def build_singularity_run_command(
    container_command,
    image,
    volumes=[],
    env=[],
    working_directory=DEFAULT_WORKING_DIRECTORY,
    singularity_cmd=DEFAULT_SINGULARITY_COMMAND,
    run_extra_arguments=DEFAULT_RUN_EXTRA_ARGUMENTS,
    sudo=DEFAULT_SUDO,
    sudo_cmd=DEFAULT_SUDO_COMMAND,
):
    command_parts = []
    # http://singularity.lbl.gov/docs-environment-metadata
    for (key, value) in env:
        command_parts.extend(["SINGULARITYENV_%s=%s" % (key, value)])
    command_parts += _singularity_prefix(
        singularity_cmd=singularity_cmd,
        sudo=sudo,
        sudo_cmd=sudo_cmd,
    )
    command_parts.append("exec")
    for volume in volumes:
        command_parts.extend(["-B", shlex_quote(str(volume))])
    if working_directory:
        command_parts.extend(["--pwd", shlex_quote(working_directory)])
    if run_extra_arguments:
        command_parts.append(run_extra_arguments)
    full_image = image
    command_parts.append(shlex_quote(full_image))
    command_parts.append(container_command)
    return " ".join(command_parts)


def _singularity_prefix(
    singularity_cmd=DEFAULT_SINGULARITY_COMMAND,
    sudo=DEFAULT_SUDO,
    sudo_cmd=DEFAULT_SUDO_COMMAND,
    **kwds
):
    """Prefix to issue a singularity command."""
    command_parts = []
    if sudo:
        command_parts.append(sudo_cmd)
    command_parts.append(singularity_cmd)
    return command_parts


__all__ = ("build_singularity_run_command",)
