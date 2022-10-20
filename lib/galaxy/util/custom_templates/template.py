"""Render customizable templates e.g. emails with Jinja

Templates are preferentially read from the ``config.templates_dir directory``.
If the requested template path cannot be resolved with respect to this
directory, the default template will be read from ``DEFAULT_TEMPLATES_DIR`` in
the Galaxy root (config/templates).
"""

import os
import logging
from jinja2 import Environment

logger = logging.getLogger(__name__)

DEFAULT_TEMPLATES_DIR = "config/templates"
TEMPLATE_SEP = '>>>>>>'  # Used to split templates into doc/body sections


def render(template_path: str, context: dict, templates_dir: str) -> str:
    """Read and return templated content as string."""
    with open(_get_template_path(template_path, templates_dir)) as f:
        template_str = f.read().split(TEMPLATE_SEP)[-1].split('\n', 1)[1]
    tmpl = Environment().from_string(template_str)
    return tmpl.render(**context)


def _get_template_path(relpath: str, custom_templates_dir: str) -> str:
    """Return template file path."""
    default_path = os.path.join(DEFAULT_TEMPLATES_DIR, relpath)
    custom_path = os.path.join(custom_templates_dir, relpath)
    logger.info(f"Custom templates_dir defined as: {custom_templates_dir}")
    if os.path.exists(custom_path):
        logger.info(f"Using custom template: {custom_path}")
        return custom_path
    return default_path


"""TODO

- [x] New conf for template_dir relative to conf_dir
- [x] Copy templates to here
- [x] Source templates from templates_dir
- [x] Default templates from config/templates
- [x] Add config exception to .gitignore: !config/templates/
- [x] Add config exception to .gitignore: !config/templates/

- [x] Jinja-fy template syntax
- [x] Add conditional rendering to templates to exclude null vars
- [x] Test
- [ ] Write tests

"""
