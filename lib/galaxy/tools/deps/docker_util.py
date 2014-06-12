
DEFAULT_DOCKER_COMMAND = "docker"
DEFAULT_SUDO = True
DEFAULT_SUDO_COMMAND = "sudo"
DEFAULT_HOST = None
DEFAULT_VOLUME_MOUNT_TYPE = "rw"
DEFAULT_WORKING_DIRECTORY = None
DEFAULT_NET = None
DEFAULT_MEMORY = None


class DockerVolume(object):

    def __init__(self, path, to_path=None, how=DEFAULT_VOLUME_MOUNT_TYPE):
        self.from_path = path
        self.to_path = to_path or path
        if not DockerVolume.__valid_how(how):
            raise ValueError("Invalid way to specify docker volume %s" % how)
        self.how = how

    @staticmethod
    def volumes_from_str(volumes_as_str):
        if not volumes_as_str:
            return []
        volume_strs = [v.strip() for v in volumes_as_str.split(",")]
        return map(DockerVolume.volume_from_str, volume_strs)

    @staticmethod
    def volume_from_str(as_str):
        if not as_str:
            raise ValueError("Failed to parse docker volume from %s" % as_str)
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


def build_docker_run_command(
    container_command,
    image,
    tag=None,
    docker_cmd=DEFAULT_DOCKER_COMMAND,
    volumes=[],
    memory=DEFAULT_MEMORY,
    env_directives=[],
    working_directory=DEFAULT_WORKING_DIRECTORY,
    sudo=DEFAULT_SUDO,
    sudo_cmd=DEFAULT_SUDO_COMMAND,
    name=None,
    host=DEFAULT_HOST,
    net=DEFAULT_NET,
):
    command_parts = []
    if sudo:
        command_parts.append(sudo_cmd)
    command_parts.append(docker_cmd)
    if host:
        command_parts.append(["-H", host])
    command_parts.append("run")
    for env_directive in env_directives:
        command_parts.extend(["-e", env_directive])
    for volume in volumes:
        command_parts.extend(["-v", str(volume)])
    if memory:
        command_parts.extend(["-m", memory])
    if name:
        command_parts.extend(["-name", name])
    if working_directory:
        command_parts.extend(["-w", working_directory])
    if net:
        command_parts.extend(["--net", net])
    full_image = image
    if tag:
        full_image = "%s:%s" % (full_image, tag)
    command_parts.append(full_image)
    command_parts.append(container_command)
    return " ".join(command_parts)
