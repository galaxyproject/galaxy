"""Locate files that tool help references by paths relative to the tool."""

import mimetypes
import os
from collections.abc import Iterable

from galaxy.util.path import (
    safe_contains,
    StrPath,
)

STATIC_IMAGES = "static/images"
# SVG can carry script, which would run on Galaxy's origin if the image were opened directly.
UNSERVED_IMAGE_TYPES = {"image/svg+xml"}


def find_tool_file(base_dir: StrPath, file_path: str) -> str | None:
    """Absolute path of the file at ``file_path`` under ``base_dir``, or ``None`` if missing or outside it."""
    # safe_contains resolves symlinks in the candidate, so compare against the resolved base.
    base_dir = os.path.realpath(base_dir)
    candidate = os.path.abspath(os.path.join(base_dir, file_path))
    if safe_contains(base_dir, candidate) and os.path.isfile(candidate):
        return candidate
    return None


def find_tool_asset(base_dir: StrPath, asset_path: str) -> str | None:
    """Find ``asset_path`` under ``base_dir``, trying ``static/images/`` first as Tool Shed help does."""
    candidates = []
    if STATIC_IMAGES not in asset_path:
        candidates.append(os.path.join(STATIC_IMAGES, asset_path))
    candidates.append(asset_path)
    for candidate in candidates:
        if found_path := find_tool_file(base_dir, candidate):
            return found_path
    return None


def find_help_image(base_dirs: Iterable[StrPath | None], image_path: str) -> str | None:
    """Find ``image_path`` under the first of ``base_dirs`` that has it, skipping unset ones."""
    for base_dir in base_dirs:
        if base_dir and (found_path := find_tool_asset(base_dir, image_path)):
            return found_path
    return None


def help_image_media_type(path: str) -> str | None:
    """Media type to serve ``path`` as a help image, or ``None`` if it isn't a servable image."""
    media_type, _ = mimetypes.guess_type(path)
    if media_type and media_type.startswith("image/") and media_type not in UNSERVED_IMAGE_TYPES:
        return media_type
    return None
