import os
import string
from abc import (
    ABCMeta,
    abstractmethod,
)
from logging import getLogger
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    TYPE_CHECKING,
)
from uuid import uuid4

from packaging.version import Version
from typing_extensions import Protocol

from galaxy.util import (
    asbool,
    in_directory,
)
from . import (
    docker_util,
    singularity_util,
)
from .container_volumes import DockerVolume
from .requirements import (
    DEFAULT_CONTAINER_RESOLVE_DEPENDENCIES,
    DEFAULT_CONTAINER_SHELL,
)

if TYPE_CHECKING:
    from .dependencies import (
        AppInfo,
        JobInfo,
        ToolInfo,
    )
    from .requirements import ContainerDescription

log = getLogger(__name__)

DOCKER_CONTAINER_TYPE = "docker"
SINGULARITY_CONTAINER_TYPE = "singularity"
TRAP_KILL_CONTAINER = "trap _on_exit EXIT"

LOAD_CACHED_IMAGE_COMMAND_TEMPLATE = r"""
python << EOF
from __future__ import print_function

import json
import re
import subprocess
import tarfile

t = tarfile.TarFile("${cached_image_file}")
meta_str = t.extractfile('repositories').read()
meta = json.loads(meta_str)
tag, tag_value = next(iter(meta.items()))
rev, rev_value = next(iter(tag_value.items()))
cmd = "${images_cmd}"
proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
stdo, stde = proc.communicate()
found = False
for line in stdo.split("\n"):
    tmp = re.split(r'\s+', line)
    if tmp[0] == tag and tmp[1] == rev and tmp[2] == rev_value:
        found = True
if not found:
    print("Loading image")
    cmd = "cat ${cached_image_file} | ${load_cmd}"
    subprocess.check_call(cmd, shell=True)
EOF
"""
SOURCE_CONDA_ACTIVATE = """
# Check if container was created by installing conda packages,
# and if so, source scripts to populate environment variables
# that would be set by activating the conda environment.
if [ -d /usr/local/etc/conda/activate.d ]; then
  export CONDA_PREFIX=/usr/local
  for f in /usr/local/etc/conda/activate.d/*.sh; do
    case "$f" in
      "/usr/local/etc/conda/activate.d/activate-"*) :;;
      *) . "$f" ;;
    esac;
  done
fi
"""


class ContainerProtocol(Protocol):
    """
    Helper class to allow typing for the HasDockerLikeVolumes mixin
    """

    @property
    def app_info(self) -> "AppInfo": ...

    @property
    def tool_info(self) -> "ToolInfo": ...

    @property
    def job_info(self) -> Optional["JobInfo"]: ...


class Container(metaclass=ABCMeta):
    """
    TODO The container resolvers currently initialize job_info as None,
    ContainerFinder.find_container fixes this by constructing a new container
    with job_info (see __destination_container)
    """

    container_type: str

    def __init__(
        self,
        container_id: str,
        app_info: "AppInfo",
        tool_info: "ToolInfo",
        destination_info: Dict[str, Any],
        job_info: Optional["JobInfo"],
        container_description: Optional["ContainerDescription"],
        container_name: Optional[str] = None,
    ) -> None:
        self.container_id = container_id
        self.app_info = app_info
        self.tool_info = tool_info
        self.destination_info = destination_info
        self.job_info = job_info
        self.container_description = container_description
        self.container_name = container_name or uuid4().hex
        self.container_info: Dict[str, Any] = {}

    def prop(self, name: str, default: Any) -> Any:
        destination_name = f"{self.container_type}_{name}"
        return self.destination_info.get(destination_name, default)

    @property
    def resolve_dependencies(self) -> bool:
        return (
            DEFAULT_CONTAINER_RESOLVE_DEPENDENCIES
            if not self.container_description
            else self.container_description.resolve_dependencies
        )

    @property
    def shell(self) -> str:
        return DEFAULT_CONTAINER_SHELL if not self.container_description else self.container_description.shell

    @property
    def source_environment(self) -> str:
        if self.container_description and not self.container_description.explicit:
            return SOURCE_CONDA_ACTIVATE
        return ""

    @abstractmethod
    def containerize_command(self, command: str) -> str:
        """
        Use destination supplied container configuration parameters,
        container_id, and command to build a new command that runs
        input command in container.
        """


class Volume:
    """
    helper class to manage a container volume string
    """

    def __init__(self, rawstr: str, container_type: str):
        self.source, self.target, self.mode = Volume.parse_volume_str(rawstr)
        self.container_type = container_type

    @staticmethod
    def parse_volume_str(rawstr: str) -> Tuple[str, str, str]:
        """
        >>> Volume.parse_volume_str('A:B:rw')
        ('A', 'B', 'rw')
        >>> Volume.parse_volume_str('A : B: ro')
        ('A', 'B', 'ro')
        >>> Volume.parse_volume_str('A:B')
        ('A', 'B', 'rw')
        >>> Volume.parse_volume_str('A:ro')
        ('A', 'A', 'ro')
        >>> Volume.parse_volume_str('A:z')
        ('A', 'A', 'z')
        >>> Volume.parse_volume_str('A:Z')
        ('A', 'A', 'Z')
        >>> Volume.parse_volume_str('A')
        ('A', 'A', 'rw')
        >>> Volume.parse_volume_str(' ')
        Traceback (most recent call last):
        ...
        Exception: Unparsable volumes string in configuration [ ]
        >>> Volume.parse_volume_str('A:B:C:D')
        Traceback (most recent call last):
        ...
        Exception: Unparsable volumes string in configuration [A:B:C:D]
        """
        if rawstr.strip() == "":
            raise Exception(f"Unparsable volumes string in configuration [{rawstr}]")

        volume_parts = rawstr.split(":")
        if len(volume_parts) > 3:
            raise Exception(f"Unparsable volumes string in configuration [{rawstr}]")
        if len(volume_parts) == 3:
            source = volume_parts[0]
            target = volume_parts[1]
            mode = volume_parts[2]
        elif len(volume_parts) == 2:
            # not really parsing/checking mode here, just figuring out if the 2nd component is target or mode
            mode_parts = volume_parts[1].split(",")
            if any(mode_part not in ("rw", "ro", "default_ro", "z", "Z") for mode_part in mode_parts):
                source = volume_parts[0]
                target = volume_parts[1]
                mode = "rw"
            else:
                source = volume_parts[0]
                target = volume_parts[0]
                mode = volume_parts[1]
        elif len(volume_parts) == 1:
            source = volume_parts[0]
            target = volume_parts[0]
            mode = "rw"

        source = source.strip()
        target = target.strip()
        mode = mode.strip()

        return source, target, mode

    def __str__(self):
        """
        >>> str(Volume('A:A:rw', 'docker'))
        'A:rw'
        >>> str(Volume('A:B:rw', 'docker'))
        'A:B:rw'
        >>> str(Volume('A:A:ro', 'singularity'))
        'A:ro'
        >>> str(Volume('A:B:ro', 'singularity'))
        'A:B:ro'
        >>> str(Volume('A:A:rw', 'singularity'))
        'A'
        >>> str(Volume('A:B:rw', 'singularity'))
        'A:B'
        """
        if self.source == self.target:
            path = self.source
        else:
            path = f"{self.source}:{self.target}"

        # TODO remove this, we require quite recent singularity anyway
        # for a while singularity did not allow to specify the bind type rw
        # (which is the default). so we omit this default
        # see https://github.com/hpcng/singularity/pull/5487
        if self.container_type == SINGULARITY_CONTAINER_TYPE and self.mode == "rw":
            return path
        else:
            return f"{path}:{self.mode}"


def preprocess_volumes(volumes_raw_str: str, container_type: str) -> List[str]:
    """Process Galaxy volume specification string to either Docker or Singularity specification.

    Galaxy allows the mount try "default_ro" which translates to ro for Docker and
    ro for Singularity iff no subdirectories are rw (Singularity does not allow ro
    parent directories with rw subdirectories).

    Removes volumes that have the same target directory which is not allowed
    (for docker and singularity). Volumes that are specified later in the volumes_raw_str
    are favoured which allows admins to overwrite defaults.

    >>> preprocess_volumes("", DOCKER_CONTAINER_TYPE)
    []
    >>> preprocess_volumes("/a/b", DOCKER_CONTAINER_TYPE)
    ['/a/b:rw']
    >>> preprocess_volumes("/a/b:ro,/a/b/c:rw", DOCKER_CONTAINER_TYPE)
    ['/a/b:ro', '/a/b/c:rw']
    >>> preprocess_volumes("/a/b:/a:ro,/a/b/c:/a/b:rw", DOCKER_CONTAINER_TYPE)
    ['/a/b:/a:ro', '/a/b/c:/a/b:rw']
    >>> preprocess_volumes("/a/b:default_ro,/a/b/c:rw", DOCKER_CONTAINER_TYPE)
    ['/a/b:ro', '/a/b/c:rw']
    >>> preprocess_volumes("/a/b:default_ro,/a/b/c:ro", SINGULARITY_CONTAINER_TYPE)
    ['/a/b:ro', '/a/b/c:ro']
    >>> preprocess_volumes("/a/b:default_ro,/a/b/c:rw", SINGULARITY_CONTAINER_TYPE)
    ['/a/b', '/a/b/c']
    >>> preprocess_volumes("/x:/a/b:default_ro,/y:/a/b/c:ro", SINGULARITY_CONTAINER_TYPE)
    ['/x:/a/b:ro', '/y:/a/b/c:ro']
    >>> preprocess_volumes("/x:/a/b:default_ro,/y:/a/b/c:rw", SINGULARITY_CONTAINER_TYPE)
    ['/x:/a/b', '/y:/a/b/c']
    >>> preprocess_volumes("/x:/x,/y:/x", SINGULARITY_CONTAINER_TYPE)
    ['/y:/x']
    """

    if not volumes_raw_str:
        return []

    volumes = [Volume(v, container_type) for v in volumes_raw_str.split(",")]
    rw_paths = [v.target for v in volumes if v.mode == "rw"]
    for volume in volumes:
        mode = volume.mode
        if volume.mode == "default_ro":
            mode = "ro"
            if container_type == SINGULARITY_CONTAINER_TYPE:
                for rw_path in rw_paths:
                    if in_directory(rw_path, volume.target):
                        mode = "rw"
        volume.mode = mode

    # remove duplicate targets
    target_to_volume = {v.target: str(v) for v in volumes}
    return list(target_to_volume.values())


class HasDockerLikeVolumes:
    """Mixin to share functionality related to Docker volume handling.

    Singularity seems to have a fairly compatible syntax for volume handling.
    """

    def _expand_volume_str(self: ContainerProtocol, value: str) -> str:
        if not value:
            return value

        template = string.Template(value)
        variables = {}

        def add_var(name, value):
            if value:
                if not value.startswith("$"):
                    value = os.path.abspath(value)
                variables[name] = value

        assert self.job_info is not None
        add_var("working_directory", self.job_info.working_directory)
        add_var("tmp_directory", self.job_info.tmp_directory)
        add_var("job_directory", self.job_info.job_directory)
        add_var("tool_directory", self.job_info.tool_directory)
        add_var("home_directory", self.job_info.home_directory)
        add_var("galaxy_root", self.app_info.galaxy_root_dir)
        add_var("default_file_path", self.app_info.default_file_path)
        add_var("library_import_dir", self.app_info.library_import_dir)
        add_var("tool_data_path", self.app_info.tool_data_path)
        add_var("galaxy_data_manager_data_path", self.app_info.galaxy_data_manager_data_path)
        add_var("shed_tool_data_path", self.app_info.shed_tool_data_path)

        if self.job_info.job_directory and self.job_info.job_directory_type == "pulsar":
            # We have a Pulsar job directory, so everything needed (excluding index
            # files) should be available in job_directory...
            defaults = "$job_directory:default_ro"
            if self.job_info.tool_directory:
                defaults += ",$tool_directory:default_ro"
            defaults += ",$job_directory/outputs:rw,$working_directory:rw"
        else:
            if self.job_info.tmp_directory is not None:
                defaults = "$tmp_directory:rw"
                # If a tool definitely has a temp directory available set it to /tmp in container for compat.
                # with CWL. This is part of that spec and should make it easier to share containers between CWL
                # and Galaxy.
                defaults += ",$tmp_directory:/tmp:rw"
            else:
                defaults = "$_GALAXY_JOB_TMP_DIR:rw,$TMPDIR:rw,$TMP:rw,$TEMP:rw"
            defaults += ",$galaxy_root:default_ro"
            if self.job_info.tool_directory:
                defaults += ",$tool_directory:default_ro"
            if self.job_info.job_directory:
                defaults += ",$job_directory:default_ro,$job_directory/outputs:rw"
                if Version(str(self.tool_info.profile)) <= Version("19.09"):
                    defaults += ",$job_directory/configs:rw"
            if self.job_info.home_directory is not None:
                defaults += ",$home_directory:rw"
            if self.app_info.outputs_to_working_directory:
                # Should need default_file_path (which is of course an estimate given
                # object stores anyway).
                defaults += ",$working_directory:rw,$default_file_path:default_ro"
            else:
                defaults += ",$working_directory:rw,$default_file_path:rw"

        if self.app_info.library_import_dir:
            defaults += ",$library_import_dir:default_ro"
        if self.app_info.tool_data_path:
            defaults += ",$tool_data_path:default_ro"
        if self.app_info.galaxy_data_manager_data_path:
            defaults += ",$galaxy_data_manager_data_path:default_ro"
        if self.app_info.shed_tool_data_path:
            defaults += ",$shed_tool_data_path:default_ro"

        # Define $defaults that can easily be extended with external library and
        # index data without deployer worrying about above details.
        variables["defaults"] = string.Template(defaults).safe_substitute(variables)

        volumes_str = template.safe_substitute(variables)

        # Not all tools have a tool_directory - strip this out if supplied by
        # job_conf.
        tool_directory_index = volumes_str.find("$tool_directory")
        if tool_directory_index > 0:
            end_index = volumes_str.find(",", tool_directory_index)
            if end_index < 0:
                end_index = len(volumes_str)
            volumes_str = volumes_str[0:tool_directory_index] + volumes_str[end_index : len(volumes_str)]

        return volumes_str


def _parse_volumes(volumes_raw: str, container_type: str) -> List[DockerVolume]:
    """
    >>> volumes_raw = "$galaxy_root:ro,$tool_directory:ro,$job_directory:ro,$working_directory:z,$default_file_path:z"
    >>> volumes = _parse_volumes(volumes_raw, "docker")
    >>> [str(v) for v in volumes]
    ['"$galaxy_root:$galaxy_root:ro"', '"$tool_directory:$tool_directory:ro"', '"$job_directory:$job_directory:ro"', '"$working_directory:$working_directory:z"', '"$default_file_path:$default_file_path:z"']
    """
    preprocessed_volumes_list = preprocess_volumes(volumes_raw, container_type)
    # TODO: Remove redundant volumes...
    return [DockerVolume.from_str(v) for v in preprocessed_volumes_list]


class DockerContainer(Container, HasDockerLikeVolumes):
    container_type = DOCKER_CONTAINER_TYPE

    @property
    def docker_host_props(self) -> Dict[str, Any]:
        docker_host_props = dict(
            docker_cmd=self.prop("cmd", docker_util.DEFAULT_DOCKER_COMMAND),
            sudo=asbool(self.prop("sudo", docker_util.DEFAULT_SUDO)),
            sudo_cmd=self.prop("sudo_cmd", docker_util.DEFAULT_SUDO_COMMAND),
            host=self.prop("host", docker_util.DEFAULT_HOST),
        )
        return docker_host_props

    @property
    def connection_configuration(self) -> Dict[str, Any]:
        return self.docker_host_props

    def build_pull_command(self) -> List[str]:
        return docker_util.build_pull_command(self.container_id, **self.docker_host_props)

    def containerize_command(self, command: str) -> str:
        env_directives = []
        for pass_through_var in self.tool_info.env_pass_through:
            env_directives.append(f'"{pass_through_var}=${pass_through_var}"')

        # Allow destinations to explicitly set environment variables just for
        # docker container. Better approach is to set for destination and then
        # pass through only what tool needs however. (See todo in ToolInfo.)
        for key, value in self.destination_info.items():
            if key.startswith("docker_env_"):
                env = key[len("docker_env_") :]
                env_directives.append(f'"{env}={value}"')

        assert self.job_info is not None
        working_directory = self.job_info.working_directory
        if not working_directory:
            raise Exception(f"Cannot containerize command [{working_directory}] without defined working directory.")

        volumes_raw = self._expand_volume_str(self.destination_info.get("docker_volumes", "$defaults"))
        volumes = _parse_volumes(volumes_raw, self.container_type)
        volumes_from = self.destination_info.get("docker_volumes_from", docker_util.DEFAULT_VOLUMES_FROM)

        docker_host_props = self.docker_host_props

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
            net=self.prop("net", None),  # By default, docker instance has networking disabled
            auto_rm=asbool(self.prop("auto_rm", docker_util.DEFAULT_AUTO_REMOVE)),
            set_user=self.prop("set_user", docker_util.DEFAULT_SET_USER),
            run_extra_arguments=self.prop("run_extra_arguments", docker_util.DEFAULT_RUN_EXTRA_ARGUMENTS),
            guest_ports=self.tool_info.guest_ports,
            container_name=self.container_name,
            **docker_host_props,
        )
        kill_command = docker_util.build_docker_simple_command(
            "kill", container_name=self.container_name, **docker_host_props
        )
        # Suppress standard error below in the kill command because it can cause jobs that otherwise would work
        # to fail. Likely, in these cases the container has been stopped normally and so cannot be stopped again.
        # A less hacky approach might be to check if the container is running first before trying to kill.
        # https://stackoverflow.com/questions/34228864/stop-and-delete-docker-container-if-its-running
        # Standard error is:
        #    Error response from daemon: Cannot kill container: 2b0b961527574ebc873256b481bbe72e: No such container: 2b0b961527574ebc873256b481bbe72e
        return f"""
_on_exit() {{
  {kill_command} &> /dev/null
}}
{TRAP_KILL_CONTAINER}
{cache_command}
{run_command}"""

    def __cache_from_file_command(self, cached_image_file: str, docker_host_props: Dict[str, Any]) -> str:
        images_cmd = docker_util.build_docker_images_command(truncate=False, **docker_host_props)
        load_cmd = docker_util.build_docker_load_command(**docker_host_props)

        return string.Template(LOAD_CACHED_IMAGE_COMMAND_TEMPLATE).safe_substitute(
            cached_image_file=cached_image_file, images_cmd=images_cmd, load_cmd=load_cmd
        )

    def __get_cached_image_file(self) -> Optional[str]:
        container_id = self.container_id
        cache_directory = os.path.abspath(self.__get_destination_overridable_property("container_image_cache_path"))
        cache_path = docker_cache_path(cache_directory, container_id)
        return cache_path if os.path.exists(cache_path) else None

    def __get_destination_overridable_property(self, name: str) -> Any:
        prop_name = f"docker_{name}"
        if prop_name in self.destination_info:
            return self.destination_info[prop_name]
        else:
            return getattr(self.app_info, name)


def docker_cache_path(cache_directory: str, container_id: str) -> str:
    file_container_id = container_id.replace("/", "_slash_")
    cache_file_name = f"docker_{file_container_id}.tar"
    return os.path.join(cache_directory, cache_file_name)


class SingularityContainer(Container, HasDockerLikeVolumes):
    container_type = SINGULARITY_CONTAINER_TYPE

    def get_singularity_target_kwds(self) -> Dict[str, Any]:
        return dict(
            singularity_cmd=self.prop("cmd", singularity_util.DEFAULT_SINGULARITY_COMMAND),
            sudo=asbool(self.prop("sudo", singularity_util.DEFAULT_SUDO)),
            sudo_cmd=self.prop("sudo_cmd", singularity_util.DEFAULT_SUDO_COMMAND),
        )

    @property
    def connection_configuration(self) -> Dict[str, Any]:
        return self.get_singularity_target_kwds()

    def build_mulled_singularity_pull_command(
        self, cache_directory: str, namespace: str = "biocontainers"
    ) -> List[str]:
        return singularity_util.pull_mulled_singularity_command(
            docker_image_identifier=self.container_id,
            cache_directory=cache_directory,
            namespace=namespace,
            **self.get_singularity_target_kwds(),
        )

    def build_singularity_pull_command(self, cache_path: str) -> List[str]:
        return singularity_util.pull_singularity_command(
            image_identifier=self.container_id, cache_path=cache_path, **self.get_singularity_target_kwds()
        )

    def containerize_command(self, command: str) -> str:
        env = []
        for pass_through_var in self.tool_info.env_pass_through:
            env.append((pass_through_var, f"${pass_through_var}"))

        # Allow destinations to explicitly set environment variables just for
        # docker container. Better approach is to set for destination and then
        # pass through only what tool needs however. (See todo in ToolInfo.)
        for key, value in self.destination_info.items():
            if key.startswith("singularity_env_"):
                real_key = key[len("singularity_env_") :]
                env.append((real_key, value))

        assert self.job_info is not None
        working_directory = self.job_info.working_directory
        if not working_directory:
            raise Exception(f"Cannot containerize command [{working_directory}] without defined working directory.")

        volumes_raw = self._expand_volume_str(self.destination_info.get("singularity_volumes", "$defaults"))
        volumes = _parse_volumes(volumes_raw, self.container_type)

        run_command = singularity_util.build_singularity_run_command(
            command,
            self.container_id,
            volumes=volumes,
            env=env,
            working_directory=working_directory,
            run_extra_arguments=self.prop("run_extra_arguments", singularity_util.DEFAULT_RUN_EXTRA_ARGUMENTS),
            guest_ports=self.tool_info.guest_ports,
            container_name=self.container_name,
            cleanenv=asbool(self.prop("cleanenv", singularity_util.DEFAULT_CLEANENV)),
            no_mount=self.prop("no_mount", singularity_util.DEFAULT_NO_MOUNT),
            **self.get_singularity_target_kwds(),
        )
        return run_command


CONTAINER_CLASSES: Dict[str, Type[Container]] = dict(
    docker=DockerContainer,
    singularity=SingularityContainer,
)
