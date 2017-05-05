import logging
import os
import string

from abc import (
    ABCMeta,
    abstractmethod
)

import six

from galaxy.util import asbool
from galaxy.util import plugin_config

from .container_resolvers.explicit import ExplicitContainerResolver
from .container_resolvers.mulled import (
    BuildMulledContainerResolver,
    CachedMulledContainerResolver,
    MulledContainerResolver,
)
from .requirements import ContainerDescription
from .requirements import DEFAULT_CONTAINER_RESOLVE_DEPENDENCIES, DEFAULT_CONTAINER_SHELL
from ..deps import docker_util

log = logging.getLogger(__name__)

DOCKER_CONTAINER_TYPE = "docker"
DEFAULT_CONTAINER_TYPE = DOCKER_CONTAINER_TYPE
ALL_CONTAINER_TYPES = [DOCKER_CONTAINER_TYPE]

LOAD_CACHED_IMAGE_COMMAND_TEMPLATE = '''
python << EOF
import re, tarfile, json, subprocess
t = tarfile.TarFile("${cached_image_file}")
meta_str = t.extractfile('repositories').read()
meta = json.loads(meta_str)
tag, tag_value = meta.items()[0]
rev, rev_value = tag_value.items()[0]
cmd = "${images_cmd}"
proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
stdo, stde = proc.communicate()
found = False
for line in stdo.split("\\n"):
    tmp = re.split(r'\s+', line)
    if tmp[0] == tag and tmp[1] == rev and tmp[2] == rev_value:
        found = True
if not found:
    print "Loading image"
    cmd = "cat ${cached_image_file} | ${load_cmd}"
    subprocess.check_call(cmd, shell=True)
EOF
'''


class ContainerFinder(object):

    def __init__(self, app_info):
        self.app_info = app_info
        self.container_registry = ContainerRegistry(app_info)

    def __enabled_container_types(self, destination_info):
        return [t for t in ALL_CONTAINER_TYPES if self.__container_type_enabled(t, destination_info)]

    def find_best_container_description(self, enabled_container_types, tool_info):
        """Regardless of destination properties - find best container for tool.

        Given container types and container.ToolInfo description of the tool."""
        container_description = self.container_registry.find_best_container_description(enabled_container_types, tool_info)
        return container_description

    def find_container(self, tool_info, destination_info, job_info):
        enabled_container_types = self.__enabled_container_types(destination_info)

        # Short-cut everything else and just skip checks if no container type is enabled.
        if not enabled_container_types:
            return NULL_CONTAINER

        def __destination_container(container_description=None, container_id=None, container_type=None):
            if container_description:
                container_id = container_description.identifier
                container_type = container_description.type
            container = self.__destination_container(
                container_id,
                container_type,
                tool_info,
                destination_info,
                job_info,
                container_description,
            )
            return container

        if "container_override" in destination_info:
            container_description = ContainerDescription.from_dict(destination_info["container_override"][0])
            if container_description:
                container = __destination_container(container_description)
                if container:
                    return container

        # If destination forcing Galaxy to use a particular container do it,
        # this is likely kind of a corner case. For instance if deployers
        # do not trust the containers annotated in tools.
        for container_type in CONTAINER_CLASSES.keys():
            container_id = self.__overridden_container_id(container_type, destination_info)
            if container_id:
                container = __destination_container(container_type=container_type, container_id=container_id)
                if container:
                    return container

        # Otherwise lets see if we can find container for the tool.
        container_description = self.find_best_container_description(enabled_container_types, tool_info)
        container = __destination_container(container_description)
        if container:
            return container

        # If we still don't have a container, check to see if any container
        # types define a default container id and use that.
        if "container" in destination_info:
            container_description = ContainerDescription.from_dict(destination_info["container"][0])
            if container_description:
                container = __destination_container(container_description)
                if container:
                    return container

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
        if "%s_container_id_override" % container_type in destination_info:
            return destination_info.get("%s_container_id_override" % container_type)
        if "%s_image_override" % container_type in destination_info:
            return self.__build_container_id_from_parts(container_type, destination_info, mode="override")

    def __build_container_id_from_parts(self, container_type, destination_info, mode):
        repo = ""
        owner = ""
        repo_key = "%s_repo_%s" % (container_type, mode)
        owner_key = "%s_owner_%s" % (container_type, mode)
        if repo_key in destination_info:
            repo = destination_info[repo_key] + "/"
        if owner_key in destination_info:
            owner = destination_info[owner_key] + "/"
        cont_id = repo + owner + destination_info["%s_image_%s" % (container_type, mode)]
        tag_key = "%s_tag_%s" % (container_type, mode)
        if tag_key in destination_info:
            cont_id += ":" + destination_info[tag_key]
        return cont_id

    def __default_container_id(self, container_type, destination_info):
        if not self.__container_type_enabled(container_type, destination_info):
            return None
        key = "%s_default_container_id" % container_type
        # Also allow docker_image...
        if key not in destination_info:
            key = "%s_image" % container_type
        if key in destination_info:
            return destination_info.get(key)
        elif "%s_image_default" in destination_info:
            return self.__build_container_id_from_parts(container_type, destination_info, mode="default")
        return None

    def __destination_container(self, container_id, container_type, tool_info, destination_info, job_info, container_description=None):
        # TODO: ensure destination_info is dict-like
        if not self.__container_type_enabled(container_type, destination_info):
            return NULL_CONTAINER

        # TODO: Right now this assumes all containers available when a
        # container type is - there should be more thought put into this.
        # Checking which are availalbe - settings policies for what can be
        # auto-fetched, etc....
        return CONTAINER_CLASSES[container_type](container_id, self.app_info, tool_info, destination_info, job_info, container_description)

    def __container_type_enabled(self, container_type, destination_info):
        return asbool(destination_info.get("%s_enabled" % container_type, False))


class NullContainerFinder(object):

    def find_container(self, tool_info, destination_info, job_info):
        return []


class ContainerRegistry(object):
    """Loop through enabled ContainerResolver plugins and find first match."""

    def __init__(self, app_info):
        self.resolver_classes = self.__resolvers_dict()
        self.enable_beta_mulled_containers = app_info.enable_beta_mulled_containers
        self.app_info = app_info
        self.container_resolvers = self.__build_container_resolvers(app_info)

    def __build_container_resolvers( self, app_info ):
        conf_file = getattr(app_info, 'containers_resolvers_config_file', None)
        if not conf_file:
            return self.__default_containers_resolvers()
        if not os.path.exists( conf_file ):
            log.debug( "Unable to find config file '%s'", conf_file)
            return self.__default_containers_resolvers()
        plugin_source = plugin_config.plugin_source_from_path( conf_file )
        return self.__parse_resolver_conf_xml( plugin_source )

    def __parse_resolver_conf_xml(self, plugin_source):
        extra_kwds = {}
        return plugin_config.load_plugins(self.resolver_classes, plugin_source, extra_kwds)

    def __default_containers_resolvers(self):
        default_resolvers = [
            ExplicitContainerResolver(self.app_info),
        ]
        if self.enable_beta_mulled_containers:
            default_resolvers.extend([
                CachedMulledContainerResolver(self.app_info),
                MulledContainerResolver(self.app_info, namespace="biocontainers"),
                BuildMulledContainerResolver(self.app_info),
            ])
        return default_resolvers

    def __resolvers_dict( self ):
        import galaxy.tools.deps.container_resolvers
        return plugin_config.plugins_dict( galaxy.tools.deps.container_resolvers, 'resolver_type' )

    def find_best_container_description(self, enabled_container_types, tool_info):
        """Yield best container description of supplied types matching tool info."""
        for container_resolver in self.container_resolvers:
            container_description = container_resolver.resolve(enabled_container_types, tool_info)
            log.info("Checking with container resolver [%s] found description [%s]" % (container_resolver, container_description))
            if container_description:
                assert container_description.type in enabled_container_types
                return container_description

        return None


class AppInfo(object):

    def __init__(
        self,
        galaxy_root_dir=None,
        default_file_path=None,
        outputs_to_working_directory=False,
        container_image_cache_path=None,
        library_import_dir=None,
        enable_beta_mulled_containers=False,
        containers_resolvers_config_file=None,
        involucro_path=None,
        involucro_auto_init=True,
    ):
        self.galaxy_root_dir = galaxy_root_dir
        self.default_file_path = default_file_path
        # TODO: Vary default value for docker_volumes based on this...
        self.outputs_to_working_directory = outputs_to_working_directory
        self.container_image_cache_path = container_image_cache_path
        self.library_import_dir = library_import_dir
        self.enable_beta_mulled_containers = enable_beta_mulled_containers
        self.containers_resolvers_config_file = containers_resolvers_config_file
        self.involucro_path = involucro_path
        self.involucro_auto_init = involucro_auto_init


class ToolInfo(object):
    # TODO: Introduce tool XML syntax to annotate the optional environment
    # variables they can consume (e.g. JVM options, license keys, etc..)
    # and add these to env_path_through

    def __init__(self, container_descriptions=[], requirements=[], requires_galaxy_python_environment=False):
        self.container_descriptions = container_descriptions
        self.requirements = requirements
        self.requires_galaxy_python_environment = requires_galaxy_python_environment
        self.env_pass_through = ["GALAXY_SLOTS"]


class JobInfo(object):

    def __init__(self, working_directory, tool_directory, job_directory, job_directory_type):
        self.working_directory = working_directory
        self.job_directory = job_directory
        # Tool files may be remote staged - so this is unintuitively a property
        # of the job not of the tool.
        self.tool_directory = tool_directory
        self.job_directory_type = job_directory_type  # "galaxy" or "pulsar"


@six.add_metaclass(ABCMeta)
class Container( object ):

    def __init__(self, container_id, app_info, tool_info, destination_info, job_info, container_description):
        self.container_id = container_id
        self.app_info = app_info
        self.tool_info = tool_info
        self.destination_info = destination_info
        self.job_info = job_info
        self.container_description = container_description

    @property
    def resolve_dependencies(self):
        return DEFAULT_CONTAINER_RESOLVE_DEPENDENCIES if not self.container_description else self.container_description.resolve_dependencies

    @property
    def shell(self):
        return DEFAULT_CONTAINER_SHELL if not self.container_description else self.container_description.shell

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
        for key, value in six.iteritems(self.destination_info):
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

        cached_image_file = self.__get_cached_image_file()
        if not cached_image_file:
            # TODO: Add option to cache it once here and create cached_image_file.
            cache_command = docker_util.build_docker_cache_command(self.container_id, **docker_host_props)
        else:
            cache_command = self.__cache_from_file_command(cached_image_file, docker_host_props)
        run_command = docker_util.build_docker_run_command(
            command,
            self.container_id,
            volumes=volumes,
            volumes_from=volumes_from,
            env_directives=env_directives,
            working_directory=working_directory,
            net=prop("net", "none"),  # By default, docker instance has networking disabled
            auto_rm=asbool(prop("auto_rm", docker_util.DEFAULT_AUTO_REMOVE)),
            set_user=prop("set_user", docker_util.DEFAULT_SET_USER),
            run_extra_arguments=prop("run_extra_arguments", docker_util.DEFAULT_RUN_EXTRA_ARGUMENTS),
            **docker_host_props
        )
        return "%s\n%s" % (cache_command, run_command)

    def __cache_from_file_command(self, cached_image_file, docker_host_props):
        images_cmd = docker_util.build_docker_images_command(truncate=False, **docker_host_props)
        load_cmd = docker_util.build_docker_load_command(**docker_host_props)

        return string.Template(LOAD_CACHED_IMAGE_COMMAND_TEMPLATE).safe_substitute(
            cached_image_file=cached_image_file,
            images_cmd=images_cmd,
            load_cmd=load_cmd
        )

    def __get_cached_image_file(self):
        container_id = self.container_id
        cache_directory = os.path.abspath(self.__get_destination_overridable_property("container_image_cache_path"))
        cache_path = docker_cache_path(cache_directory, container_id)
        return cache_path if os.path.exists(cache_path) else None

    def __get_destination_overridable_property(self, name):
        prop_name = "docker_%s" % name
        if prop_name in self.destination_info:
            return self.destination_info[prop_name]
        else:
            return getattr(self.app_info, name)

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
        add_var("library_import_dir", self.app_info.library_import_dir)

        if self.job_info.job_directory and self.job_info.job_directory_type == "pulsar":
            # We have a Pulsar job directory, so everything needed (excluding index
            # files) should be available in job_directory...
            defaults = "$job_directory:ro,$tool_directory:ro,$job_directory/outputs:rw,$working_directory:rw"
        else:
            defaults = "$galaxy_root:ro,$tool_directory:ro"
            if self.job_info.job_directory:
                defaults += ",$job_directory:ro"
            if self.app_info.outputs_to_working_directory:
                # Should need default_file_path (which is a course estimate given
                # object stores anyway).
                defaults += ",$working_directory:rw,$default_file_path:ro"
            else:
                defaults += ",$working_directory:rw,$default_file_path:rw"

        if self.app_info.library_import_dir:
            defaults += ",$library_import_dir:ro"

        # Define $defaults that can easily be extended with external library and
        # index data without deployer worrying about above details.
        variables["defaults"] = string.Template(defaults).safe_substitute(variables)

        return template.safe_substitute(variables)


def docker_cache_path(cache_directory, container_id):
    file_container_id = container_id.replace("/", "_slash_")
    cache_file_name = "docker_%s.tar" % file_container_id
    return os.path.join(cache_directory, cache_file_name)


CONTAINER_CLASSES = dict(
    docker=DockerContainer,
)


class NullContainer(object):

    def __init__(self):
        pass

    def __bool__(self):
        return False
    __nonzero__ = __bool__


NULL_CONTAINER = NullContainer()
