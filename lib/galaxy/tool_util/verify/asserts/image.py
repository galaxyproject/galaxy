import io
from typing import (
    Optional,
    Union,
)

from PIL import Image


def assert_has_image_metadata(
    output_bytes: bytes,
    width: Optional[Union[int,str]] = None,
    height: Optional[Union[int,str]] = None,
    channels: Optional[Union[int,str]] = None,
) -> None:
    """
    Assert the specified image output has specific metadata.
    """
    buf = io.BytesIO(output_bytes)
    with Image.open(buf) as im:

        assert width is None or im.size[0] == int(width), \
            f"Image has wrong width: {im.size[0]} (expected {int(width)})"

        assert height is None or im.size[1] == int(height), \
            f"Image has wrong height: {im.size[1]} (expected {int(height)})"

        actual_channels = len(im.getbands())
        assert channels is None or actual_channels == int(channels), \
            f"Image has wrong number of channels: {actual_channels} (expected {int(channels)})"