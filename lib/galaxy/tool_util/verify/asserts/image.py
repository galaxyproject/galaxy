from typing import (
    Optional,
)

from PIL import Image


def assert_has_image_metadata(
    output_bytes: bytes,
    width: Optional[int] = None,
) -> None:
    """Asserts the specified image output has a specific width"""
    buf = io.BytesIO(output_bytes)
    with Image.open(buf) as im:
        assert width is None or im.size[0] == width,
            "Image has wrong width: {im.size[0]} (expected {width})"