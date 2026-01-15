"""GCP Batch runner utilities and templates."""

from string import Template

from galaxy.util.resources import resource_string

from .helpers import (
    DEFAULT_CPU_MILLI,
    DEFAULT_CVMFS_DOCKER_VOLUME,
    DEFAULT_MEMORY_MIB,
    DEFAULT_NFS_MOUNT_PATH,
    DEFAULT_NFS_PATH,
    convert_cpu_to_milli,
    convert_memory_to_mib,
    parse_docker_volumes_param,
    parse_volume_spec,
    parse_volumes_param,
    sanitize_label_value,
)

CONTAINER_SCRIPT_TEMPLATE = Template(resource_string(__name__, "container_script.sh"))
DIRECT_SCRIPT_TEMPLATE = Template(resource_string(__name__, "direct_script.sh"))

__all__ = (
    "CONTAINER_SCRIPT_TEMPLATE",
    "DEFAULT_CPU_MILLI",
    "DEFAULT_CVMFS_DOCKER_VOLUME",
    "DEFAULT_MEMORY_MIB",
    "DEFAULT_NFS_MOUNT_PATH",
    "DEFAULT_NFS_PATH",
    "DIRECT_SCRIPT_TEMPLATE",
    "convert_cpu_to_milli",
    "convert_memory_to_mib",
    "parse_docker_volumes_param",
    "parse_volume_spec",
    "parse_volumes_param",
    "sanitize_label_value",
)
