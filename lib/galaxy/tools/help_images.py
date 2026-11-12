"""Locate files shipped with a tool, such as its icon and help images."""

import os

from galaxy.util.path import (
    safe_contains,
    StrPath,
)

STATIC_IMAGES = "static/images"


def find_tool_file(base_dir: StrPath, file_path: str) -> str | None:
    """Absolute path of the file at ``file_path`` under ``base_dir``, or ``None`` if missing or outside it."""
    # safe_contains resolves symlinks in the candidate, so compare against the resolved base.
    base_dir = os.path.realpath(base_dir)
    candidate = os.path.abspath(os.path.join(base_dir, file_path))
    if safe_contains(base_dir, candidate) and os.path.isfile(candidate):
        return candidate
    return None


def find_tool_asset(base_dir: str, asset_path: str) -> str | None:
    """Find ``asset_path`` under ``base_dir``, trying ``static/images/`` first as Tool Shed help does."""
    candidates = []
    if STATIC_IMAGES not in asset_path:
        candidates.append(os.path.join(base_dir, STATIC_IMAGES, asset_path))
    candidates.append(os.path.join(base_dir, asset_path))
    for candidate in candidates:
        candidate = os.path.abspath(candidate)
        if safe_contains(base_dir, candidate) and os.path.isfile(candidate):
            return candidate
    return None
