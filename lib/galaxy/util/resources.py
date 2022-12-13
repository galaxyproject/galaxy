"""Provide a consistent interface into and utilities for importlib file resources.
"""
try:
    from importlib.abc import Traversable  # type: ignore[attr-defined]
    from importlib.resources import files  # type: ignore[attr-defined]
except ImportError:
    # Python < 3.9
    from importlib_resources import files  # type: ignore[no-redef]
    from importlib_resources.abc import Traversable  # type: ignore[no-redef]


def resource_path(package_or_requirement, resource_name):
    """
    Return specified resource as a string.

    Replacement function for pkg_resources.resource_string, but returns unicode string instead of bytestring.
    """
    return files(package_or_requirement).joinpath(resource_name)


def resource_string(package_or_requirement, resource_name) -> str:
    """
    Return specified resource as a string.

    Replacement function for pkg_resources.resource_string, but returns unicode string instead of bytestring.
    """
    return resource_path(package_or_requirement, resource_name).read_text()


__all__ = (
    "files",
    "resource_string",
    "resource_path",
    "Traversable",
)
