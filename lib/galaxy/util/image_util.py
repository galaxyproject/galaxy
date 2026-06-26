"""Provides utilities for working with image files."""

import logging

try:
    from PIL import Image
except ImportError:
    Image = None  # type: ignore[assignment, unused-ignore]

log = logging.getLogger(__name__)


def image_type(filename: str) -> str | None:
    fmt = None
    if Image is not None:
        try:
            with Image.open(filename) as im:
                fmt = im.format
        except Exception:
            pass
    if fmt:
        return fmt.upper()
    else:
        return None


def check_image_type(filename: str, types: list[str]) -> bool:
    fmt = image_type(filename)
    if fmt in types:
        return True
    return False
