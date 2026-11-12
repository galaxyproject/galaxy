"""Locate files that tool help references by paths relative to the tool."""

import os

from galaxy.util.path import safe_contains

STATIC_IMAGES = "static/images"


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
