import io
from typing import (
    Optional,
    Union,
    List
)

import numpy
from PIL import Image


def assert_image_has_metadata(
    output_bytes: bytes,
    width: Optional[Union[int,str]] = None,
    height: Optional[Union[int,str]] = None,
    channels: Optional[Union[int,str]] = None,
) -> None:
    """
    Assert the image output has specific metadata.
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


def assert_image_has_labels(
    output_bytes: bytes,
    number_of_objects: Optional[Union[int, str]] = None,
    mean_object_size: Optional[Union[float, str]] = None,
    exclude_labels: Optional[Union[str, List[int]]] = list(),
    eps: Optional[Union[float, str]] = 1e-8,
) -> None:
    """
    Assert the image output has specific label content.
    """
    buf = io.BytesIO(output_bytes)
    with Image.open(buf) as im:
        im_arr = numpy.array(im)
    
    # Determine labels present in the image.
    labels = numpy.unique(im_arr)

    # Apply filtering induced by `exclude_labels`.
    if isinstance(exclude_labels, str):
        exclude_labels = [im_arr.dtype(label) for label in exclude_labels.split(",") if len(label) > 0]
    labels = [label for label in labels if label is not in exclude_labels]

    # Perform `number_of_objects` assertion.
    if number_of_objects is not None:
        actual = len(labels)
        expected = int(number_of_objects)
        assert actual == expected, \
            f"Wrong number of objects: {actual} (expected {expected})"

    # Perform `mean_object_size` assertion.
    if mean_object_size is not None:
        actual = numpy.mean((im_arr == label).sum() for label in labels)
        expected = float(mean_object_size)
        assert abs(actual - expected) <= float(eps), \
            f"Wrong mean object size: {actual} (expected {expected})"