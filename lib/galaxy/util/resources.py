"""Provide a consistent interface into and utilities for importlib file resources.
"""

import sys

if sys.version_info >= (3, 9):
    from importlib.resources import (
        as_file,
        files,
        Package as Anchor,
    )

    if sys.version_info >= (3, 12):
        from importlib.resources.abc import Traversable
    else:
        from importlib.abc import Traversable
else:
    from importlib_resources import (
        as_file,
        files,
        Package as Anchor,
    )
    from importlib_resources.abc import Traversable


def resource_path(package_or_requirement: Anchor, resource_name: str) -> Traversable:
    """
    Return specified resource as a Traversable.
    """
    return files(package_or_requirement).joinpath(resource_name)


def resource_string(package_or_requirement: Anchor, resource_name: str) -> str:
    """
    Return specified resource as a string.

    Replacement function for pkg_resources.resource_string, but returns unicode string instead of bytestring.
    """
    return resource_path(package_or_requirement, resource_name).read_text()


__all__ = (
    "as_file",
    "files",
    "resource_string",
    "resource_path",
    "Traversable",
)
