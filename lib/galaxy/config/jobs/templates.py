"""Templating abstraction around jinja2 for galaxy.config.jobs."""

from jinja2 import Template


def render(template_str: str, **kwds):
    """Use jinja2 to render specified template."""
    template = Template(template_str)
    contents = template.render(**kwds)
    return contents
