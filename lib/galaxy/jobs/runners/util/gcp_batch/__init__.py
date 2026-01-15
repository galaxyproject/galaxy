"""GCP Batch runner utilities and templates."""

from string import Template

from galaxy.util.resources import resource_string

from .helpers import (
    convert_cpu_to_milli,
    convert_memory_to_mib,
    sanitize_label_value,
)

CONTAINER_SCRIPT_TEMPLATE = Template(resource_string(__name__, "container_script.sh"))
DIRECT_SCRIPT_TEMPLATE = Template(resource_string(__name__, "direct_script.sh"))

__all__ = (
    "CONTAINER_SCRIPT_TEMPLATE",
    "DIRECT_SCRIPT_TEMPLATE",
    "convert_cpu_to_milli",
    "convert_memory_to_mib",
    "sanitize_label_value",
)
