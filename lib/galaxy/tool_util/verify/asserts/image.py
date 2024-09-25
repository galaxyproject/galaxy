import io
from typing import (
    Any,
    List,
    Optional,
    Tuple,
    TYPE_CHECKING,
    Union,
)

from ._types import (
    Annotated,
    AssertionParameter,
    Negate,
    NEGATE_DEFAULT,
    OptionalXmlFloat,
    OptionalXmlInt,
    OutputBytes,
    XmlFloat,
    XmlInt,
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
try:
    import tifffile
except ImportError:
    pass

if TYPE_CHECKING:
    import numpy.typing


JSON_STRICT_NUMBER = "typing.Union[StrictInt, StrictFloat]"
JSON_OPTIONAL_STRICT_NUMBER = f"typing.Optional[{JSON_STRICT_NUMBER}]"


Width = Annotated[
    OptionalXmlInt,
    AssertionParameter(
        "Expected width of the image (in pixels).",
        json_type="typing.Optional[StrictInt]",
        xml_type="xs:nonNegativeInteger",
        validators=["check_non_negative_if_set"],
    ),
]
Height = Annotated[
    OptionalXmlInt,
    AssertionParameter(
        "Expected height of the image (in pixels).",
        json_type="typing.Optional[StrictInt]",
        xml_type="xs:nonNegativeInteger",
        validators=["check_non_negative_if_set"],
    ),
]
Channels = Annotated[
    OptionalXmlInt,
    AssertionParameter(
        "Expected number of channels of the image.",
        json_type="typing.Optional[StrictInt]",
        xml_type="xs:nonNegativeInteger",
        validators=["check_non_negative_if_set"],
    ),
]
WidthDelta = Annotated[
    XmlInt,
    AssertionParameter(
        "Maximum allowed difference of the image width (in pixels, default is 0). The observed width has to be in the range ``value +- delta``.",
        json_type="StrictInt",
        xml_type="xs:nonNegativeInteger",
        validators=["check_non_negative_if_set"],
    ),
]
WidthMin = Annotated[
    OptionalXmlInt,
    AssertionParameter(
        "Minimum allowed width of the image (in pixels).",
        json_type="typing.Optional[StrictInt]",
        xml_type="xs:nonNegativeInteger",
        validators=["check_non_negative_if_set"],
    ),
]
WidthMax = Annotated[
    OptionalXmlInt,
    AssertionParameter(
        "Maximum allowed width of the image (in pixels).",
        json_type="typing.Optional[StrictInt]",
        xml_type="xs:nonNegativeInteger",
        validators=["check_non_negative_if_set"],
    ),
]
HeightDelta = Annotated[
    XmlInt,
    AssertionParameter(
        "Maximum allowed difference of the image height (in pixels, default is 0). The observed height has to be in the range ``value +- delta``.",
        json_type="StrictInt",
        xml_type="xs:nonNegativeInteger",
        validators=["check_non_negative_if_set"],
    ),
]
HeightMin = Annotated[
    OptionalXmlInt,
    AssertionParameter(
        "Minimum allowed height of the image (in pixels).",
        json_type="typing.Optional[StrictInt]",
        xml_type="xs:nonNegativeInteger",
        validators=["check_non_negative_if_set"],
    ),
]
HeightMax = Annotated[
    OptionalXmlInt,
    AssertionParameter(
        "Maximum allowed height of the image (in pixels).",
        json_type="typing.Optional[StrictInt]",
        xml_type="xs:nonNegativeInteger",
        validators=["check_non_negative_if_set"],
    ),
]
ChannelsDelta = Annotated[
    XmlInt,
    AssertionParameter(
        "Maximum allowed difference of the number of channels (default is 0). The observed number of channels has to be in the range ``value +- delta``.",
        json_type="StrictInt",
        xml_type="xs:nonNegativeInteger",
        validators=["check_non_negative_if_set"],
    ),
]
ChannelsMin = Annotated[
    OptionalXmlInt,
    AssertionParameter(
        "Minimum allowed number of channels.",
        json_type="typing.Optional[StrictInt]",
        xml_type="xs:nonNegativeInteger",
        validators=["check_non_negative_if_set"],
    ),
]
ChannelsMax = Annotated[
    OptionalXmlInt,
    AssertionParameter(
        "Maximum allowed number of channels.",
        json_type="typing.Optional[StrictInt]",
        xml_type="xs:nonNegativeInteger",
        validators=["check_non_negative_if_set"],
    ),
]
MeanIntensity = Annotated[
    OptionalXmlFloat,
    AssertionParameter("The required mean value of the image intensities.", json_type=JSON_OPTIONAL_STRICT_NUMBER),
]
MeanIntensityEps = Annotated[
    XmlFloat,
    AssertionParameter(
        "The absolute tolerance to be used for ``value`` (defaults to ``0.01``). The observed mean value of the image intensities has to be in the range ``value +- eps``.",
        json_type=JSON_STRICT_NUMBER,
        validators=["check_non_negative_if_set"],
    ),
]
MeanIntensityMin = Annotated[
    OptionalXmlFloat,
    AssertionParameter(
        "A lower bound of the required mean value of the image intensities.", json_type=JSON_OPTIONAL_STRICT_NUMBER
    ),
]
MeanIntensityMax = Annotated[
    OptionalXmlFloat,
    AssertionParameter(
        "An upper bound of the required mean value of the image intensities.", json_type=JSON_OPTIONAL_STRICT_NUMBER
    ),
]
NumLabels = Annotated[
    OptionalXmlInt,
    AssertionParameter(
        "Expected number of labels.",
        json_type="typing.Optional[StrictInt]",
        xml_type="xs:nonNegativeInteger",
        validators=["check_non_negative_if_set"],
    ),
]
NumLabelsDelta = Annotated[
    XmlInt,
    AssertionParameter(
        "Maximum allowed difference of the number of labels (default is 0). The observed number of labels has to be in the range ``value +- delta``.",
        json_type="StrictInt",
        xml_type="xs:nonNegativeInteger",
        validators=["check_non_negative_if_set"],
    ),
]
NumLabelsMin = Annotated[
    OptionalXmlInt,
    AssertionParameter(
        "Minimum allowed number of labels.",
        json_type="typing.Optional[StrictInt]",
        xml_type="xs:nonNegativeInteger",
        validators=["check_non_negative_if_set"],
    ),
]
NumLabelsMax = Annotated[
    OptionalXmlInt,
    AssertionParameter(
        "Maximum allowed number of labels.",
        json_type="typing.Optional[StrictInt]",
        xml_type="xs:nonNegativeInteger",
        validators=["check_non_negative_if_set"],
    ),
]

Channel = Annotated[
    OptionalXmlInt,
    AssertionParameter(
        "Restricts the assertion to a specific channel of the image (where ``0`` corresponds to the first image channel).",
        json_type="typing.Optional[StrictInt]",
    ),
]
CenterOfMass = Annotated[
    str,
    AssertionParameter(
        "The required center of mass of the image intensities (horizontal and vertical coordinate, separated by a comma).",
        validators=["check_center_of_mass"],
    ),
]
CenterOfMassEps = Annotated[
    XmlFloat,
    AssertionParameter(
        "The maximum allowed Euclidean distance to the required center of mass (defaults to ``0.01``).",
        json_type=JSON_STRICT_NUMBER,
        validators=["check_non_negative_if_set"],
    ),
]
Labels = Annotated[
    Optional[Union[str, List[int]]],
    AssertionParameter(
        "List of labels, separated by a comma. Labels *not* on this list will be excluded from consideration. Cannot be used in combination with ``exclude_labels``.",
        xml_type="xs:string",
        json_type="typing.Optional[typing.List[int]]",
    ),
]
ExcludeLabels = Annotated[
    Optional[Union[str, List[int]]],
    AssertionParameter(
        "List of labels to be excluded from consideration, separated by a comma. The primary usage of this attribute is to exclude the background of a label image. Cannot be used in combination with ``labels``.",
        xml_type="xs:string",
        json_type="typing.Optional[typing.List[int]]",
    ),
]
MeanObjectSize = Annotated[
    OptionalXmlFloat,
    AssertionParameter(
        "The required mean size of the uniquely labeled objects.",
        xml_type="xs:float",
        json_type=JSON_OPTIONAL_STRICT_NUMBER,
        validators=["check_non_negative_if_set"],
    ),
]
MeanObjectSizeEps = Annotated[
    XmlFloat,
    AssertionParameter(
        "The absolute tolerance to be used for ``value`` (defaults to ``0.01``). The observed mean size of the uniquely labeled objects has to be in the range ``value +- eps``.",
        xml_type="xs:float",
        json_type=JSON_STRICT_NUMBER,
        validators=["check_non_negative_if_set"],
    ),
]
MeanObjectSizeMin = Annotated[
    OptionalXmlFloat,
    AssertionParameter(
        "A lower bound of the required mean size of the uniquely labeled objects.",
        xml_type="xs:float",
        json_type=JSON_OPTIONAL_STRICT_NUMBER,
        validators=["check_non_negative_if_set"],
    ),
]
MeanObjectSizeMax = Annotated[
    OptionalXmlFloat,
    AssertionParameter(
        "An upper bound of the required mean size of the uniquely labeled objects.",
        xml_type="xs:float",
        json_type=JSON_OPTIONAL_STRICT_NUMBER,
        validators=["check_non_negative_if_set"],
    ),
]


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
    output_bytes: OutputBytes,
    width: Width = None,
    delta: WidthDelta = 0,
    min: WidthMin = None,
    max: WidthMax = None,
    negate: Negate = NEGATE_DEFAULT,
) -> None:
    """Asserts the output is an image and has a specific width (in pixels).

    The width is plus/minus ``delta`` (e.g., ``<has_image_width width="512" delta="2" />``).
    Alternatively the range of the expected width can be specified by ``min`` and/or ``max``.
    """
    im_arr = _get_image(output_bytes)
    _assert_number(
        im_arr.shape[1],
        width,
        delta,
        min,
        max,
        negate,
        "{expected} width {n}+-{delta}",
        "{expected} width to be in [{min}:{max}]",
    )


def assert_has_image_height(
    output_bytes: bytes,
    height: Height = None,
    delta: HeightDelta = 0,
    min: HeightMin = None,
    max: HeightMax = None,
    negate: Negate = NEGATE_DEFAULT,
) -> None:
    """Asserts the output is an image and has a specific height (in pixels).

    The height is plus/minus ``delta`` (e.g., ``<has_image_height height="512" delta="2" />``).
    Alternatively the range of the expected height can be specified by ``min`` and/or ``max``.
    """
    im_arr = _get_image(output_bytes)
    _assert_number(
        im_arr.shape[0],
        height,
        delta,
        min,
        max,
        negate,
        "{expected} height {n}+-{delta}",
        "{expected} height to be in [{min}:{max}]",
    )


def assert_has_image_channels(
    output_bytes: bytes,
    channels: Channels = None,
    delta: ChannelsDelta = 0,
    min: ChannelsMin = None,
    max: ChannelsMax = None,
    negate: Negate = NEGATE_DEFAULT,
) -> None:
    """Asserts the output is an image and has a specific number of channels.

    The number of channels is plus/minus ``delta`` (e.g., ``<has_image_channels channels="3" />``).

    Alternatively the range of the expected number of channels can be specified by ``min`` and/or ``max``.
    """
    im_arr = _get_image(output_bytes)
    n_channels = 1 if im_arr.ndim < 3 else im_arr.shape[2]  # we assume here that the image is a 2-D image
    _assert_number(
        n_channels,
        channels,
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

    The function tries to read the image using tifffile and Pillow.
    """
    buf = io.BytesIO(output_bytes)

    # Try reading with tifffile first. It fails if the file is not a TIFF.
    try:
        with tifffile.TiffFile(buf) as im_file:
            assert len(im_file.series) == 1, f'Image has unsupported number of series: {len(im_file.series)}'
            im_axes = im_file.series[0].axes

            # Verify that the image format is supported
            assert frozenset('XY') <= frozenset(im_axes) <= frozenset('XYCS'), f'Image has unsupported axes: {im_axes}'

            # Treat sample axis "S" as channel axis "C" and fail if both are present
            assert 'C' not in im_axes or 'S' not in im_axes, f'Image has sample and channel axes which is not supported: {im_axes}'
            im_axes = im_axes.replace('S', 'C')

            # Read the image data
            im_arr = im_file.asarray()

            # Normalize order of axes Y and X
            ypos = im_axes.find('Y')
            xpos = im_axes.find('X')
            if ypos > xpos:
                im_arr = im_arr.swapaxes(ypos, xpos)

            # Normalize image axes to YXC
            cpos = im_axes.find('C')
            if -1 < cpos < 2:
                im_arr = numpy.rollaxis(im_arr, cpos, 3)

    # If tifffile failed, then the file is not a tifffile. In that case, try with Pillow.
    except tifffile.TiffFileError:
        buf.seek(0)
        with Image.open(buf) as im:
            im_arr = numpy.array(im)

            # Verify that the image format is supported
            assert im_arr.ndim in (2, 3), f'Image has unsupported dimension: {im_arr.ndim}'

    # Select the specified channel (if any).
    if channel is not None:
        im_arr = im_arr[:, :, int(channel)]

    # Return the image
    return im_arr


def assert_has_image_mean_intensity(
    output_bytes: OutputBytes,
    channel: Channel = None,
    mean_intensity: MeanIntensity = None,
    eps: MeanIntensityEps = 0.01,
    min: MeanIntensityMin = None,
    max: MeanIntensityMax = None,
) -> None:
    """Asserts the output is an image and has a specific mean intensity value.

    The mean intensity value is plus/minus ``eps`` (e.g., ``<has_image_mean_intensity mean_intensity="0.83" />``).
    Alternatively the range of the expected mean intensity value can be specified by ``min`` and/or ``max``.
    """
    im_arr = _get_image(output_bytes, channel)
    _assert_float(
        actual=im_arr.mean(),
        label="mean intensity",
        tolerance=eps,
        expected=mean_intensity,
        range_min=min,
        range_max=max,
    )


def assert_has_image_center_of_mass(
    output_bytes: OutputBytes,
    center_of_mass: CenterOfMass,
    channel: Channel = None,
    eps: CenterOfMassEps = 0.01,
) -> None:
    """Asserts the specified output is an image and has the specified center of mass.

    Asserts the output is an image and has a specific center of mass,
    or has an Euclidean distance of ``eps`` or less to that point (e.g.,
    ``<has_image_center_of_mass center_of_mass="511.07, 223.34" />``).
    """
    im_arr = _get_image(output_bytes, channel)
    center_of_mass_parts = [c.strip() for c in center_of_mass.split(",")]
    assert len(center_of_mass_parts) == 2
    center_of_mass_tuple = (float(center_of_mass_parts[0]), float(center_of_mass_parts[1]))
    assert len(center_of_mass_tuple) == 2, "center_of_mass must have two components"
    actual_center_of_mass = _compute_center_of_mass(im_arr)
    distance = numpy.linalg.norm(numpy.subtract(center_of_mass_tuple, actual_center_of_mass))
    assert distance <= float(
        eps
    ), f"Wrong center of mass: {actual_center_of_mass} (expected {center_of_mass}, distance: {distance}, eps: {eps})"


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
        labels = []
    if isinstance(labels, str):
        labels = [cast_label(label) for label in labels.split(",") if len(label) > 0]
    if len(labels) > 0:
        present_labels = [label for label in present_labels if label in labels]

    # Apply filtering due to `exclude_labels`.
    if exclude_labels is None:
        exclude_labels = []
    if isinstance(exclude_labels, str):
        exclude_labels = [cast_label(label) for label in exclude_labels.split(",") if len(label) > 0]
    present_labels = [label for label in present_labels if label not in exclude_labels]

    # Return the image data and the labels.
    return im_arr, present_labels


def assert_has_image_n_labels(
    output_bytes: OutputBytes,
    channel: Channel = None,
    labels: Labels = None,
    exclude_labels: ExcludeLabels = None,
    n: NumLabels = None,
    delta: NumLabelsDelta = 0,
    min: NumLabelsMin = None,
    max: NumLabelsMax = None,
    negate: Negate = NEGATE_DEFAULT,
) -> None:
    """Asserts the output is an image and has the specified labels.

    Labels can be a number of labels or unique values (e.g.,
    ``<has_image_n_labels n="187" exclude_labels="0" />``).

    The primary usage of this assertion is to verify the number of objects in images with uniquely labeled objects.
    """
    present_labels = _get_image_labels(output_bytes, channel, labels, exclude_labels)[1]
    _assert_number(
        len(present_labels),
        n,
        delta,
        min,
        max,
        negate,
        "{expected} labels {n}+-{delta}",
        "{expected} labels to be in [{min}:{max}]",
    )


def assert_has_image_mean_object_size(
    output_bytes: OutputBytes,
    channel: Channel = None,
    labels: Labels = None,
    exclude_labels: ExcludeLabels = None,
    mean_object_size: MeanObjectSize = None,
    eps: MeanObjectSizeEps = 0.01,
    min: MeanObjectSizeMin = None,
    max: MeanObjectSizeMax = None,
) -> None:
    """Asserts the output is an image with labeled objects which have the specified mean size (number of pixels),

    The mean size is plus/minus ``eps`` (e.g., ``<has_image_mean_object_size mean_object_size="111.87" exclude_labels="0" />``).

    The labels must be unique.
    """
    im_arr, present_labels = _get_image_labels(output_bytes, channel, labels, exclude_labels)
    actual_mean_object_size = sum((im_arr == label).sum() for label in present_labels) / len(present_labels)
    _assert_float(
        actual=actual_mean_object_size,
        label="mean object size",
        tolerance=eps,
        expected=mean_object_size,
        range_min=min,
        range_max=max,
    )
