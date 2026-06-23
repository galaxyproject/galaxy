"""Provide a consistent interface into and utilities for importlib file resources."""

import sys

if sys.version_info >= (3, 12):
    from importlib.resources import (
        as_file,
        files,
    )
    from importlib.resources.abc import Traversable

    if sys.version_info >= (3, 13):
        from importlib.resources import Anchor
    else:
        from importlib.resources import Package as Anchor
else:
    from importlib_resources import (
        as_file,
        files,
        Package as Anchor,
    )
    from importlib_resources.abc import Traversable


def resource_path(anchor: Anchor, resource_name: str) -> Traversable:
    """
    Return specified resource as a Traversable.

    anchor is either a module object or a module name as a string.
    """
    return files(anchor).joinpath(resource_name)


def resource_string(anchor: Anchor, resource_name: str) -> str:
    """
    Return specified resource as a string.

    Replacement function for pkg_resources.resource_string, but returns unicode string instead of bytestring.

    anchor is either a module object or a module name as a string.
    """
    return resource_path(anchor, resource_name).read_text()


__all__ = (
    "as_file",
    "files",
    "resource_string",
    "resource_path",
    "Traversable",
)
