"""Utilities for building up Docker commands...

...using common defaults and configuration mechanisms.
"""
import os

from six.moves import shlex_quote

from .commands import argv_to_str

DEFAULT_DOCKER_COMMAND = "docker"
DEFAULT_SUDO = True
DEFAULT_SUDO_COMMAND = "sudo"
DEFAULT_HOST = None
DEFAULT_VOLUME_MOUNT_TYPE = "rw"
DEFAULT_WORKING_DIRECTORY = None
DEFAULT_NET = None
DEFAULT_MEMORY = None
DEFAULT_VOLUMES_FROM = None
DEFAULT_AUTO_REMOVE = True
DEFAULT_SET_USER = "$UID"
DEFAULT_RUN_EXTRA_ARGUMENTS = None


class DockerVolume(object):

    def __init__(self, path, to_path=None, how=DEFAULT_VOLUME_MOUNT_TYPE):
        self.from_path = path
        self.to_path = to_path or path
        if not DockerVolume.__valid_how(how):
            raise ValueError("Invalid way to specify Docker volume %s" % how)
        self.how = how

    @staticmethod
    def volumes_from_str(volumes_as_str):
        if not volumes_as_str:
            return []
        volume_strs = [v.strip() for v in volumes_as_str.split(",")]
        return [DockerVolume.volume_from_str(_) for _ in volume_strs]

    @staticmethod
    def volume_from_str(as_str):
        if not as_str:
            raise ValueError("Failed to parse Docker volume from %s" % as_str)
        parts = as_str.split(":", 2)
        kwds = dict(path=parts[0])
        if len(parts) == 2:
            if DockerVolume.__valid_how(parts[1]):
                kwds["how"] = parts[1]
            else:
                kwds["to_path"] = parts[1]
        elif len(parts) == 3:
            kwds["to_path"] = parts[1]
            kwds["how"] = parts[2]
        return DockerVolume(**kwds)

    @staticmethod
    def __valid_how(how):
        return how in ["ro", "rw"]

    def __str__(self):
        return ":".join([self.from_path, self.to_path, self.how])


def kill_command(
    container,
    signal=None,
    **kwds
):
    args = (["-s", signal] if signal else []) + [container]
    return command_list("kill", args, **kwds)


def logs_command(
    container,
    **kwds
):
    return command_list("logs", **kwds)


def build_command(
    image,
    docker_build_path,
    **kwds
):
    if os.path.isfile(docker_build_path):
        docker_build_path = os.path.dirname(os.path.abspath(docker_build_path))
    return command_list("build", ["-t", image, docker_build_path], **kwds)


def build_save_image_command(
    image,
    destination,
    **kwds
):
    return command_list("save", ["-o", destination, image], **kwds)


def build_pull_command(
    tag,
    **kwds
):
    return command_list("pull", [tag], **kwds)


def build_docker_cache_command(
    image,
    **kwds
):
    inspect_image_command = command_shell("inspect", [image], **kwds)
    pull_image_command = command_shell("pull", [image], **kwds)
    cache_command = "%s > /dev/null 2>&1\n[ $? -ne 0 ] && %s > /dev/null 2>&1\n" % (inspect_image_command, pull_image_command)
    return cache_command


def build_docker_images_command(truncate=True, **kwds):
    args = ["--no-trunc"] if not truncate else[]
    return command_shell("images", args, **kwds)


def build_docker_load_command(**kwds):
    return command_shell("load", [])


def build_docker_run_command(
    container_command,
    image,
    interactive=False,
    terminal=False,
    tag=None,
    volumes=[],
    volumes_from=DEFAULT_VOLUMES_FROM,
    memory=DEFAULT_MEMORY,
    env_directives=[],
    working_directory=DEFAULT_WORKING_DIRECTORY,
    name=None,
    net=DEFAULT_NET,
    run_extra_arguments=DEFAULT_RUN_EXTRA_ARGUMENTS,
    docker_cmd=DEFAULT_DOCKER_COMMAND,
    sudo=DEFAULT_SUDO,
    sudo_cmd=DEFAULT_SUDO_COMMAND,
    auto_rm=DEFAULT_AUTO_REMOVE,
    set_user=DEFAULT_SET_USER,
    host=DEFAULT_HOST,
):
    command_parts = _docker_prefix(
        docker_cmd=docker_cmd,
        sudo=sudo,
        sudo_cmd=sudo_cmd,
        host=host
    )
    command_parts.append("run")
    if interactive:
        command_parts.append("-i")
    if terminal:
        command_parts.append("-t")
    for env_directive in env_directives:
        # e.g. -e "GALAXY_SLOTS=$GALAXY_SLOTS"
        # These are environment variable expansions so we don't quote these.
        command_parts.extend(["-e", env_directive])
    for volume in volumes:
        command_parts.extend(["-v", shlex_quote(str(volume))])
    if volumes_from:
        command_parts.extend(["--volumes-from", shlex_quote(str(volumes_from))])
    if memory:
        command_parts.extend(["-m", shlex_quote(memory)])
    if name:
        command_parts.extend(["--name", shlex_quote(name)])
    if working_directory:
        command_parts.extend(["-w", shlex_quote(working_directory)])
    if net:
        command_parts.extend(["--net", shlex_quote(net)])
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

            user = "%d:%d" % (euid, egid)
        command_parts.extend(["--user", user])
    full_image = image
    if tag:
        full_image = "%s:%s" % (full_image, tag)
    command_parts.append(shlex_quote(full_image))
    command_parts.append(container_command)
    return " ".join(command_parts)


def command_list(command, command_args=[], **kwds):
    """Return Docker command as an argv list."""
    command_parts = _docker_prefix(**kwds)
    command_parts.append(command)
    command_parts.extend(command_args)
    return command_parts


def command_shell(command, command_args=[], **kwds):
    """Return Docker command as a string for a shell."""
    return argv_to_str(command_list(command, command_args, **kwds))


def _docker_prefix(
    docker_cmd=DEFAULT_DOCKER_COMMAND,
    sudo=DEFAULT_SUDO,
    sudo_cmd=DEFAULT_SUDO_COMMAND,
    host=DEFAULT_HOST,
    **kwds
):
    """Prefix to issue a docker command."""
    command_parts = []
    if sudo:
        command_parts.append(sudo_cmd)
    command_parts.append(docker_cmd)
    if host:
        command_parts.extend(["-H", host])
    return command_parts
