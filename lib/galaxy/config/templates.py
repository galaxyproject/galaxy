"""Render customizable templates e.g. emails with Jinja.

Templates are preferentially read from a custom template directory (the value
of `templates_dir`, passed to the `render` function). If the requested
template path cannot be resolved with respect to this directory, the default
template will be read from `config/templates` in the Galaxy root.

Templates may ``{% include %}`` partials (shared template fragments). Partials
are resolved via a Jinja loader with the same custom-first, package-default
precedence as the main template. Partials are pure template body (they do not
use the ``>>>>>>`` doc-header convention), so they are looked up directly by the
loader rather than through :func:`_get_template_body`.
"""

from pathlib import Path

from jinja2 import (
    ChoiceLoader,
    Environment,
    FileSystemLoader,
    PackageLoader,
)

from galaxy.util.resources import (
    resource_path,
    Traversable,
)

TEMPLATE_SEP = ">>>>>>"  # Used to split templates into doc/body sections

#: Loader for ``{% include %}`` partials: custom templates dir first, then the
#: package's bundled ``templates`` directory. Matches the custom-first
#: precedence of :func:`_get_template_path`. Built lazily-free per call (the
#: custom dir varies per render call) -- cheap to construct.
_PACKAGE_TEMPLATES_LOADER = PackageLoader("galaxy.config", "templates")


def _build_loader(custom_templates_dir: str) -> ChoiceLoader:
    return ChoiceLoader([FileSystemLoader(custom_templates_dir), _PACKAGE_TEMPLATES_LOADER])


def render(
    template_path: str,
    context: dict,
    custom_templates_dir: str,
    autoescape: bool | None = None,
) -> str:
    """Read and return templated content as string.

    ``autoescape`` defaults to ``True`` for HTML templates to prevent XSS.
    Plain-text (``.txt``) templates must never be autoescaped: when left at the
    default (``None``) they render unescaped, and explicitly passing
    ``autoescape=True`` for a ``.txt`` template is a programming error that
    raises ``ValueError`` rather than being silently ignored. When autoescape is
    enabled, template authors who intentionally inject trusted HTML must mark
    the value with the ``| safe`` filter.

    The rendered template may ``{% include %}`` partials; those are resolved
    via a loader with the same custom-first precedence (see module docstring).
    Autoescape applies to partial output as well, inheriting the parent
    environment's setting.
    """
    with _get_template_path(template_path, custom_templates_dir).open() as f:
        template_str = _get_template_body(f.read())
    if template_path.endswith(".txt"):
        if autoescape is True:
            raise ValueError(
                f"Plain-text templates must never be autoescaped; got autoescape=True for '{template_path}'."
            )
        autoescape = False
    elif autoescape is None:
        autoescape = True
    env = Environment(autoescape=autoescape, loader=_build_loader(custom_templates_dir))
    tmpl = env.from_string(template_str)
    return tmpl.render(**context)


def _get_template_body(template: str) -> str:
    """Remove comment/doc header to return the template body."""
    return template.split(TEMPLATE_SEP, 1)[-1].split("\n", 1)[1]


def _get_template_path(relpath: str, custom_templates_dir: str) -> Traversable:
    """Return template file path."""
    default_path = resource_path(__name__, "templates") / relpath
    custom_path = Path(custom_templates_dir) / relpath
    if custom_path.exists():
        return custom_path
    return default_path
