"""Render customizable templates e.g. emails with Jinja

Templates are preferentially read from the ``templates_dir`` directory.
If the requested template path cannot be resolved with respect to this
directory, the default template will be read from ``DEFAULT_TEMPLATES_DIR`` in
the Galaxy root (config/templates).
"""

import os
from pathlib import Path

from jinja2 import Environment

DEFAULT_TEMPLATES_DIR = Path("lib/galaxy/config/templates")
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


def _get_template_path(relpath: str, custom_templates_dir: str) -> str:
    """Return template file path."""
    default_path = _get_default_templates_dir() / relpath
    custom_path = os.path.join(custom_templates_dir, relpath)
    if os.path.exists(custom_path):
        return custom_path
    return default_path


def _get_default_templates_dir() -> Path:
    """Return path to default template dir.

    Accounts for running in ./packages dir when running tests.
    """
    if DEFAULT_TEMPLATES_DIR.exists:
        return DEFAULT_TEMPLATES_DIR
    return ".." / DEFAULT_TEMPLATES_DIR
