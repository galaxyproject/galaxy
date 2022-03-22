"""Provides utilities for working with image files."""

import imghdr
import logging

try:
    import Image as PIL
except ImportError:
    try:
        from PIL import Image as PIL
    except ImportError:
        PIL = None

log = logging.getLogger(__name__)


def image_type(filename):
    fmt = None
    if PIL is not None:
        try:
            im = PIL.open(filename)
            fmt = im.format
            im.close()
        except Exception:
            # We continue to try with imghdr, so this is a rare case of an
            # exception we expect to happen frequently, so we're not logging
            pass
    if not fmt:
        fmt = imghdr.what(filename)
    if fmt:
        return fmt.upper()
    else:
        return False


def check_image_type(filename, types):
    fmt = image_type(filename)
    if fmt in types:
        return True
    return False
