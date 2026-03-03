"""GCP Batch runner utilities and templates."""

from string import Template

from galaxy.util.resources import resource_string
from .helpers import (
    compute_machine_type,
    convert_cpu_to_milli,
    convert_duration_to_seconds,
    convert_memory_to_mib,
    DEFAULT_CPU_MILLI,
    DEFAULT_CVMFS_DOCKER_VOLUME,
    DEFAULT_MAX_RUN_DURATION,
    DEFAULT_MEMORY_MIB,
    DEFAULT_NFS_MOUNT_PATH,
    DEFAULT_NFS_PATH,
    parse_docker_volumes_param,
    parse_volume_spec,
    parse_volumes_param,
    resolve_max_run_duration,
    sanitize_label_value,
)

CONTAINER_SCRIPT_TEMPLATE = Template(resource_string(__name__, "container_script.sh"))
DIRECT_SCRIPT_TEMPLATE = Template(resource_string(__name__, "direct_script.sh"))

__all__ = (
    "CONTAINER_SCRIPT_TEMPLATE",
    "DEFAULT_CPU_MILLI",
    "DEFAULT_CVMFS_DOCKER_VOLUME",
    "DEFAULT_MAX_RUN_DURATION",
    "DEFAULT_MEMORY_MIB",
    "DEFAULT_NFS_MOUNT_PATH",
    "DEFAULT_NFS_PATH",
    "DIRECT_SCRIPT_TEMPLATE",
    "compute_machine_type",
    "convert_cpu_to_milli",
    "convert_memory_to_mib",
    "convert_to_duration",
    "parse_docker_volumes_param",
    "resolve_max_run_duration",
    "parse_volume_spec",
    "parse_volumes_param",
    "sanitize_label_value",
)
