"""Load Galaxy interactive tour definitions.

Shared by Galaxy's tour registry and by the browser automation that walks tours.
"""

import os
from collections.abc import Callable
from functools import cache
from typing import Any

import yaml

from galaxy.util.path import StrPath
from .components import Component
from .data import load_root_component

WarnCallback = Callable[[str], None]


def noop_warn(message: str) -> None:
    pass


@cache
def _root_component() -> Component:
    return load_root_component()


def get_tour_id_from_path(tour_path: StrPath) -> str:
    filename = os.path.basename(tour_path)
    return os.path.splitext(filename)[0]


def load_tour_steps(
    contents_dict: dict[str, Any], warn: WarnCallback | None = None, resolve_components: bool = True
) -> None:
    warn = warn or noop_warn
    #  Some of this can be done on the clientside.  Maybe even should?
    title_default = contents_dict.get("title_default")
    if "requirements" not in contents_dict:
        contents_dict["requirements"] = []

    for step in contents_dict["steps"]:
        # Remove attributes no longer used, so they are attempted to be
        # validated.
        if "backdrop" in step:
            warn(f"Deprecated and dropped property backdrop found in step {step}")
            step.pop("backdrop")

        if "component" in step and resolve_components:
            component = step.pop("component")
            step["element"] = _root_component().resolve_component_locator(component).locator

        if "intro" in step:
            step["content"] = step.pop("intro")
        if "position" in step:
            step["placement"] = step.pop("position")
        if "element" not in step:
            step["orphan"] = True
        if title_default and "title" not in step:
            step["title"] = title_default


def load_tour_from_path(
    tour_path: StrPath, warn: WarnCallback | None = None, resolve_components: bool = True
) -> dict[str, Any]:
    with open(tour_path) as f:
        tour: dict[str, Any] = yaml.safe_load(f)
        load_tour_steps(tour, warn=warn, resolve_components=resolve_components)
    return tour
