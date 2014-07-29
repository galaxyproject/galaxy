from abc import (
    ABCMeta,
    abstractmethod
)
import os
import string

from galaxy.util import asbool
from ..deps import docker_util

import logging
log = logging.getLogger(__name__)

DEFAULT_CONTAINER_TYPE = "docker"


class ContainerFinder(object):

    def __init__(self, app_info):
        self.app_info = app_info
        self.container_registry = ContainerRegistry()

    def find_container(self, tool_info, destination_info, job_info):
        def __destination_container(container_description=None, container_id=None, container_type=None):
            if container_description:
                container_id = container_description.identifier
                container_type = container_description.type
            container = self.__destination_container(
                container_id,
                container_type,
                tool_info,
                destination_info,
                job_info
            )
            return container

        # Is destination forcing Galaxy to use a particular container do it,
        # this is likely kind of a corner case. For instance if deployers
        # do not trust the containers annotated in tools.
        for container_type in CONTAINER_CLASSES.keys():
            container_id = self.__overridden_container_id(container_type, destination_info)
            if container_id:
                container = __destination_container(container_type=container_type, container_id=container_id)
                if container:
                    return container

        # Otherwise lets see if we can find container for the tool.

        # Exact matches first from explicitly listed containers in tools...
        for container_description in tool_info.container_descriptions:
            container = __destination_container(container_description)
            if container:
                return container

        # Implement vague concept of looping through all containers
        # matching requirements. Exact details need to be worked through
        # but hopefully the idea that it sits below find_container somewhere
        # external components to this module don't need to worry about it
        # is good enough.
        container_descriptions = self.container_registry.container_descriptions_for_requirements(tool_info.requirements)
        for container_description in container_descriptions:
            container = __destination_container(container_description)
            if container:
                return container

        # If we still don't have a container, check to see if any container
        # types define a default container id and use that.
        for container_type in CONTAINER_CLASSES.keys():
            container_id = self.__default_container_id(container_type, destination_info)
            if container_id:
                container = __destination_container(container_type=container_type, container_id=container_id)
                if container:
                    return container

        return NULL_CONTAINER

    def __overridden_container_id(self, container_type, destination_info):
        if not self.__container_type_enabled(container_type, destination_info):
            return None
        return destination_info.get("%s_container_id_override" % container_type)

    def __default_container_id(self, container_type, destination_info):
        if not self.__container_type_enabled(container_type, destination_info):
            return None
        return destination_info.get("%s_default_container_id" % container_type)

    def __destination_container(self, container_id, container_type, tool_info, destination_info, job_info):
        # TODO: ensure destination_info is dict-like
        if not self.__container_type_enabled(container_type, destination_info):
            return NULL_CONTAINER

        # TODO: Right now this assumes all containers available when a
        # container type is - there should be more thought put into this.
        # Checking which are availalbe - settings policies for what can be
        # auto-fetched, etc....
        return CONTAINER_CLASSES[container_type](container_id, self.app_info, tool_info, destination_info, job_info)

    def __container_type_enabled(self, container_type, destination_info):
        return asbool(destination_info.get("%s_enabled" % container_type, False))


class NullContainerFinder(object):

    def find_container(self, tool_info, destination_info, job_info):
        return []


class ContainerRegistry():

    def __init__(self):
        pass

    def container_descriptions_for_requirements(self, requirements):
        # Return lists of containers that would match requirements...
        return []


class AppInfo(object):

    def __init__(self, galaxy_root_dir=None, default_file_path=None, outputs_to_working_directory=False):
        self.galaxy_root_dir = galaxy_root_dir
        self.default_file_path = default_file_path
        # TODO: Vary default value for docker_volumes based on this...
        self.outputs_to_working_directory = outputs_to_working_directory


class ToolInfo(object):
    # TODO: Introduce tool XML syntax to annotate the optional environment
    # variables they can consume (e.g. JVM options, license keys, etc..)
    # and add these to env_path_through

    def __init__(self, container_descriptions=[], requirements=[]):
        self.container_descriptions = container_descriptions
        self.requirements = requirements
        self.env_pass_through = ["GALAXY_SLOTS"]


class JobInfo(object):

    def __init__(self, working_directory, tool_directory, job_directory):
        self.working_directory = working_directory
        self.job_directory = job_directory
        # Tool files may be remote staged - so this is unintuitively a property
        # of the job not of the tool.
        self.tool_directory = tool_directory


class Container( object ):
    __metaclass__ = ABCMeta

    def __init__(self, container_id, app_info, tool_info, destination_info, job_info):
        self.container_id = container_id
        self.app_info = app_info
        self.tool_info = tool_info
        self.destination_info = destination_info
        self.job_info = job_info

    @abstractmethod
    def containerize_command(self, command):
        """
        Use destination supplied container configuration parameters,
        container_id, and command to build a new command that runs
        input command in container.
        """


class DockerContainer(Container):

    def containerize_command(self, command):
        def prop(name, default):
            destination_name = "docker_%s" % name
            return self.destination_info.get(destination_name, default)

        env_directives = []
        for pass_through_var in self.tool_info.env_pass_through:
            env_directives.append('"%s=$%s"' % (pass_through_var, pass_through_var))

        # Allow destinations to explicitly set environment variables just for
        # docker container. Better approach is to set for destination and then
        # pass through only what tool needs however. (See todo in ToolInfo.)
        for key, value in self.destination_info.iteritems():
            if key.startswith("docker_env_"):
                env = key[len("docker_env_"):]
                env_directives.append('"%s=%s"' % (env, value))

        working_directory = self.job_info.working_directory
        if not working_directory:
            raise Exception("Cannot containerize command [%s] without defined working directory." % working_directory)

        volumes_raw = self.__expand_str(self.destination_info.get("docker_volumes", "$defaults"))
        # TODO: Remove redundant volumes...
        volumes = docker_util.DockerVolume.volumes_from_str(volumes_raw)
        volumes_from = self.destination_info.get("docker_volumes_from", docker_util.DEFAULT_VOLUMES_FROM)

        docker_host_props = dict(
            docker_cmd=prop("cmd", docker_util.DEFAULT_DOCKER_COMMAND),
            sudo=asbool(prop("sudo", docker_util.DEFAULT_SUDO)),
            sudo_cmd=prop("sudo_cmd", docker_util.DEFAULT_SUDO_COMMAND),
            host=prop("host", docker_util.DEFAULT_HOST),
        )

        cache_command = docker_util.build_docker_cache_command(self.container_id, **docker_host_props)
        run_command = docker_util.build_docker_run_command(
            command,
            self.container_id,
            volumes=volumes,
            volumes_from=volumes_from,
            env_directives=env_directives,
            working_directory=working_directory,
            net=prop("net", "none"),  # By default, docker instance has networking disabled
            **docker_host_props
        )
        return "%s\n%s" % (cache_command, run_command)

    def __expand_str(self, value):
        if not value:
            return value

        template = string.Template(value)
        variables = dict()

        def add_var(name, value):
            if value:
                variables[name] = os.path.abspath(value)

        add_var("working_directory", self.job_info.working_directory)
        add_var("job_directory", self.job_info.job_directory)
        add_var("tool_directory", self.job_info.tool_directory)
        add_var("galaxy_root", self.app_info.galaxy_root_dir)
        add_var("default_file_path", self.app_info.default_file_path)

        if self.job_info.job_directory:
            # We have a job directory, so everything needed (excluding index
            # files) should be available in job_directory...
            defaults = "$job_directory:ro,$tool_directory:ro,$job_directory/outputs:rw,$working_directory:rw"
        elif self.app_info.outputs_to_working_directory:
            # Should need default_file_path (which is a course estimate given
            # object stores anyway.
            defaults = "$galaxy_root:ro,$tool_directory:ro,$working_directory:rw,$default_file_path:ro"
        else:
            defaults = "$galaxy_root:ro,$tool_directory:ro,$working_directory:rw,$default_file_path:rw"

        # Define $defaults that can easily be extended with external library and
        # index data without deployer worrying about above details.
        variables["defaults"] = string.Template(defaults).safe_substitute(variables)

        return template.safe_substitute(variables)


CONTAINER_CLASSES = dict(
    docker=DockerContainer,
)


class NullContainer(object):

    def __init__(self):
        pass

    def __nonzero__(self):
        return False


NULL_CONTAINER = NullContainer()
