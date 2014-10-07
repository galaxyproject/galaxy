import os

from ..deps import commands
from ..deps import docker_util
from ..deps.requirements import parse_requirements_from_xml
from ...tools import loader_directory

import logging
log = logging.getLogger(__name__)


def docker_host_args(**kwds):
    return dict(
        docker_cmd=kwds["docker_cmd"],
        sudo=kwds["docker_sudo"],
        sudo_cmd=kwds["docker_sudo_cmd"],
        host=kwds["docker_host"]
    )


def dockerfile_build(path, dockerfile=None, error=log.error, **kwds):
    expected_container_names = set()
    for (tool_path, tool_xml) in loader_directory.load_tool_elements_from_path(path):
        requirements, containers = parse_requirements_from_xml(tool_xml)
        for container in containers:
            if container.type == "docker":
                expected_container_names.add(container.identifier)
                break

    if len(expected_container_names) == 0:
        error("Could not find any docker identifiers to generate.")

    if len(expected_container_names) > 1:
        error("Multiple different docker identifiers found for selected tools [%s]", expected_container_names)

    image_identifier = expected_container_names.pop()
    if dockerfile is None:
        dockerfile = "Dockerfile"

    docker_command_parts = docker_util.build_command(
        image_identifier,
        dockerfile,
        **docker_host_args(**kwds)
    )
    commands.execute(docker_command_parts)
    docker_image_cache = kwds['docker_image_cache']
    if docker_image_cache:
        destination = os.path.join(docker_image_cache, image_identifier + ".tar")
        save_image_command_parts = docker_util.build_save_image_command(
            image_identifier,
            destination,
            **docker_host_args(**kwds)
        )
        commands.execute(save_image_command_parts)
