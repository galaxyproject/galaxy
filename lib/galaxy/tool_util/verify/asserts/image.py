import io
from typing import (
    Any,
    List,
    Optional,
    Tuple,
    TYPE_CHECKING,
    Union,
)

from ._util import _assert_number

try:
    import numpy
except ImportError:
    pass
try:
    from PIL import Image
except ImportError:
    pass

if TYPE_CHECKING:
    import numpy.typing


def _assert_float(
    actual: float,
    label: str,
    tolerance: Union[float, str],
    expected: Optional[Union[float, str]] = None,
    range_min: Optional[Union[float, str]] = None,
    range_max: Optional[Union[float, str]] = None,
) -> None:

    # Perform `tolerance` based check.
    if expected is not None:
        assert abs(actual - float(expected)) <= float(
            tolerance
        ), f"Wrong {label}: {actual} (expected {expected} ±{tolerance})"

    # Perform `range_min` based check.
    if range_min is not None:
        assert actual >= float(range_min), f"Wrong {label}: {actual} (must be {range_min} or larger)"

    # Perform `range_max` based check.
    if range_max is not None:
        assert actual <= float(range_max), f"Wrong {label}: {actual} (must be {range_max} or smaller)"


def assert_has_image_width(
    output_bytes: bytes,
    value: Optional[Union[int, str]] = None,
    delta: Union[int, str] = 0,
    min: Optional[Union[int, str]] = None,
    max: Optional[Union[int, str]] = None,
    negate: Union[bool, str] = False,
) -> None:
    """
    Asserts the specified output is an image and has a width of the specified value.
    """
    buf = io.BytesIO(output_bytes)
    with Image.open(buf) as im:
        _assert_number(
            im.size[0],
            value,
            delta,
            min,
            max,
            negate,
            "{expected} width {n}+-{delta}",
            "{expected} width to be in [{min}:{max}]",
        )


def assert_has_image_height(
    output_bytes: bytes,
    value: Optional[Union[int, str]] = None,
    delta: Union[int, str] = 0,
    min: Optional[Union[int, str]] = None,
    max: Optional[Union[int, str]] = None,
    negate: Union[bool, str] = False,
) -> None:
    """
    Asserts the specified output is an image and has a height of the specified value.
    """
    buf = io.BytesIO(output_bytes)
    with Image.open(buf) as im:
        _assert_number(
            im.size[1],
            value,
            delta,
            min,
            max,
            negate,
            "{expected} height {n}+-{delta}",
            "{expected} height to be in [{min}:{max}]",
        )


def assert_has_image_channels(
    output_bytes: bytes,
    value: Optional[Union[int, str]] = None,
    delta: Union[int, str] = 0,
    min: Optional[Union[int, str]] = None,
    max: Optional[Union[int, str]] = None,
    negate: Union[bool, str] = False,
) -> None:
    """
    Asserts the specified output is an image and has the specified number of channels.
    """
    buf = io.BytesIO(output_bytes)
    with Image.open(buf) as im:
        _assert_number(
            len(im.getbands()),
            value,
            delta,
            min,
            max,
            negate,
            "{expected} image channels {n}+-{delta}",
            "{expected} image channels to be in [{min}:{max}]",
        )


def _compute_center_of_mass(im_arr: "numpy.typing.NDArray") -> Tuple[float, float]:
    while im_arr.ndim > 2:
        im_arr = im_arr.sum(axis=2)
    im_arr = numpy.abs(im_arr)
    if im_arr.sum() == 0:
        return (numpy.nan, numpy.nan)
    im_arr = im_arr / im_arr.sum()
    yy, xx = numpy.indices(im_arr.shape)
    return (im_arr * xx).sum(), (im_arr * yy).sum()


def _get_image(
    output_bytes: bytes,
    channel: Optional[Union[int, str]] = None,
) -> "numpy.typing.NDArray":
    """
    Returns the output image or a specific channel.
    """
    buf = io.BytesIO(output_bytes)
    with Image.open(buf) as im:
        im_arr = numpy.array(im)

    # Select the specified channel (if any).
    if channel is not None:
        im_arr = im_arr[:, :, int(channel)]

    # Return the image
    return im_arr


def assert_has_image_mean_intensity(
    output_bytes: bytes,
    channel: Optional[Union[int, str]] = None,
    value: Optional[Union[float, str]] = None,
    delta: Union[float, str] = 0.01,
    min: Optional[Union[float, str]] = None,
    max: Optional[Union[float, str]] = None,
) -> None:
    """
    Asserts the specified output is an image and has the specified mean intensity value.
    """
    im_arr = _get_image(output_bytes, channel)
    _assert_float(
        actual=im_arr.mean(),
        label="mean intensity",
        tolerance=delta,
        expected=value,
        range_min=min,
        range_max=max,
    )


def assert_has_image_center_of_mass(
    output_bytes: bytes,
    channel: Optional[Union[int, str]] = None,
    point: Optional[Union[Tuple[float, float], str]] = None,
    delta: Union[float, str] = 0.01,
) -> None:
    """
    Asserts the specified output is an image and has the specified center of mass.
    """
    im_arr = _get_image(output_bytes, channel)
    if point is not None:
        if isinstance(point, str):
            point_parts = [c.strip() for c in point.split(",")]
            assert len(point_parts) == 2
            point = (float(point_parts[0]), float(point_parts[1]))
        assert len(point) == 2, "point must have two components"
        actual_center_of_mass = _compute_center_of_mass(im_arr)
        distance = numpy.linalg.norm(numpy.subtract(point, actual_center_of_mass))
        assert distance <= float(
            delta
        ), f"Wrong center of mass: {actual_center_of_mass} (expected {point}, distance: {distance}, delta: {delta})"


def _get_image_labels(
    output_bytes: bytes,
    channel: Optional[Union[int, str]] = None,
    labels: Optional[Union[str, List[int]]] = None,
    exclude_labels: Optional[Union[str, List[int]]] = None,
) -> Tuple["numpy.typing.NDArray", List[Any]]:
    """
    Determines the unique labels in the output image or a specific channel.
    """
    assert labels is None or exclude_labels is None
    im_arr = _get_image(output_bytes, channel)

    def cast_label(label):
        label = label.strip()
        if numpy.issubdtype(im_arr.dtype, numpy.integer):
            return int(label)
        if numpy.issubdtype(im_arr.dtype, float):
            return float(label)
        raise AssertionError(f'Unsupported image label type: "{im_arr.dtype}"')

    # Determine labels present in the image.
    present_labels = numpy.unique(im_arr)

    # Apply filtering due to `labels` (keep only those).
    if labels is None:
        labels = list()
    if isinstance(labels, str):
        labels = [cast_label(label) for label in labels.split(",") if len(label) > 0]
    if len(labels) > 0:
        present_labels = [label for label in present_labels if label in labels]

    # Apply filtering due to `exclude_labels`.
    if exclude_labels is None:
        exclude_labels = list()
    if isinstance(exclude_labels, str):
        exclude_labels = [cast_label(label) for label in exclude_labels.split(",") if len(label) > 0]
    present_labels = [label for label in present_labels if label not in exclude_labels]

    # Return the image data and the labels.
    return im_arr, present_labels


def assert_has_image_labels(
    output_bytes: bytes,
    channel: Optional[Union[int, str]] = None,
    exclude_labels: Optional[Union[str, List[int]]] = None,
    value: Optional[Union[int, str]] = None,
    delta: Union[int, str] = 0,
    min: Optional[Union[int, str]] = None,
    max: Optional[Union[int, str]] = None,
    negate: Union[bool, str] = False,
) -> None:
    """
    Asserts the specified output is an image and has the specified number of unique values (e.g., uniquely labeled objects).
    """
    present_labels = _get_image_labels(output_bytes, channel, exclude_labels)[1]
    _assert_number(
        len(present_labels),
        value,
        delta,
        min,
        max,
        negate,
        "{expected} labels {n}+-{delta}",
        "{expected} labels to be in [{min}:{max}]",
    )


def assert_has_image_mean_object_size(
    output_bytes: bytes,
    channel: Optional[Union[int, str]] = None,
    labels: Optional[Union[str, List[int]]] = None,
    exclude_labels: Optional[Union[str, List[int]]] = None,
    value: Optional[Union[float, str]] = None,
    delta: Union[float, str] = 0.01,
    min: Optional[Union[float, str]] = None,
    max: Optional[Union[float, str]] = None,
) -> None:
    """
    Asserts the specified output is an image with labeled objects which have the specified mean size (number of pixels).
    """
    im_arr, present_labels = _get_image_labels(output_bytes, channel, labels, exclude_labels)
    actual_mean_object_size = sum((im_arr == label).sum() for label in present_labels) / len(present_labels)
    _assert_float(
        actual=actual_mean_object_size,
        label="mean object size",
        tolerance=delta,
        expected=value,
        range_min=min,
        range_max=max,
    )
