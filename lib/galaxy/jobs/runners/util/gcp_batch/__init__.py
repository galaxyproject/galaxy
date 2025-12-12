"""GCP Batch runner utilities and templates."""

from string import Template

from galaxy.util.resources import resource_string

CONTAINER_SCRIPT_TEMPLATE = Template(resource_string(__name__, "container_script.sh"))
DIRECT_SCRIPT_TEMPLATE = Template(resource_string(__name__, "direct_script.sh"))
