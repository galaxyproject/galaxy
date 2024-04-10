"""Provides utilities for working with image files."""

import imghdr
import logging
from typing import (
    List,
    Optional,
)

try:
    from PIL import Image
except ImportError:
    Image = None  # type: ignore[assignment, unused-ignore]

log = logging.getLogger(__name__)


def image_type(filename: str) -> Optional[str]:
    fmt = None
    if Image is not None:
        try:
            with Image.open(filename) as im:
                fmt = im.format
        except Exception:
            # We continue to try with imghdr, so this is a rare case of an
            # exception we expect to happen frequently, so we're not logging
            pass
    if not fmt:
        fmt = imghdr.what(filename)
    if fmt:
        return fmt.upper()
    else:
        return None


def check_image_type(filename: str, types: List[str]) -> bool:
    fmt = image_type(filename)
    if fmt in types:
        return True
    return False
