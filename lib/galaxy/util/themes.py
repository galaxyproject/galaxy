from typing import (
    Dict,
    Union,
)

Theme = Dict[str, Union["Theme", str]]


def flatten_theme(theme: Theme, prefix: str = "-") -> Dict[str, str]:
    """Transforms a nested theme dictionary into a flat dictionary,
    containing keys compatible with css variables. e.g. '--masthead-background-color'"""
    flat_attributes: Dict[str, str] = {}

    for key, val in theme.items():
        if isinstance(val, str):
            flat_attributes[f"{prefix}-{key}"] = val
        elif isinstance(val, Dict):
            flat_attributes.update(flatten_theme(val, f"{prefix}-{key}"))

    return flat_attributes


# Built-in themes seeded into ``config.themes`` regardless of ``themes_config_file``
# (which has no sample fallback, so an admin with no themes_conf.yml has none).
# Admin config may override a built-in by redefining its key.
#
# ``orbit`` mirrors the Orbit shell palette (app/src/renderer/styles.css :root) so an
# embedded Galaxy Page rendered inside Orbit's dark chrome reads as part of the shell.
# Its ``content`` block flattens to ``--content-*`` css variables consumed by the page
# / markdown render stack; the ``masthead`` block keeps ``orbit`` a complete, normally
# selectable theme too.
BUILTIN_THEMES: Dict[str, Theme] = {
    "orbit": {
        "masthead": {
            "color": "#2c3143",
            "text": {
                "color": "#f0f2f8",
                "hover": "#ffd700",
                "active": "#ffffff",
            },
            "link": {
                "color": "transparent",
                "hover": "transparent",
                "active": "#181a24",
            },
            "logo": {
                "img": "/static/favicon.svg",
                "img-secondary": None,
            },
        },
        "content": {
            "background": "#2c3143",
            "surface": "#343a50",
            "text": "#f0f2f8",
            "text-muted": "rgba(240, 242, 248, 0.55)",
            "heading": "#f8fafc",
            "border": "rgba(255, 255, 255, 0.12)",
            "link": "#ffd700",
            "link-hover": "#ffe450",
        },
    },
}


def flattened_builtin_themes() -> Dict[str, Dict[str, str]]:
    """Built-in themes as flat css-variable dicts, ready to seed ``config.themes``."""
    return {key: flatten_theme(theme) for key, theme in BUILTIN_THEMES.items()}
