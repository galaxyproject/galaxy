import io
from typing import (
    Optional,
    Union,
)

from PIL import Image


def assert_has_image_metadata(
    output_bytes: bytes,
    width: Optional[Union[int,str]] = None,
) -> None:
    """Asserts the specified image output has a specific width"""
    buf = io.BytesIO(output_bytes)
    with Image.open(buf) as im:
        assert width is None or im.size[0] == int(width), \
            f"Image has wrong width: {im.size[0]} (expected {int(width)})"

    # len(image.getbands())