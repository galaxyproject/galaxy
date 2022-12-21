"""Render customizable templates e.g. emails with Jinja.

Templates are preferentially read from a custom template directory (the value
of `templates_dir`, passed to the `render` function). If the requested
template path cannot be resolved with respect to this directory, the default
template will be read from `config/templates` in the Galaxy root.
"""

from pathlib import Path

from jinja2 import Environment

from galaxy.util.resources import resource_path

TEMPLATE_SEP = ">>>>>>"  # Used to split templates into doc/body sections


def render(template_path: str, context: dict, custom_templates_dir: str) -> str:
    """Read and return templated content as string."""
    with open(_get_template_path(template_path, custom_templates_dir)) as f:
        template_str = _get_template_body(f.read())
    tmpl = Environment().from_string(template_str)
    return tmpl.render(**context)


def _get_template_body(template: str) -> str:
    """Remove comment/doc header to return the template body."""
    return template.split(TEMPLATE_SEP, 1)[-1].split("\n", 1)[1]


def _get_template_path(relpath: str, custom_templates_dir: str) -> Path:
    """Return template file path."""
    default_path = resource_path("galaxy.config", "templates") / relpath
    custom_path = Path(custom_templates_dir) / relpath
    if custom_path.exists():
        return custom_path
    return default_path
