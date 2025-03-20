from ._types import (
    Annotated,
    AssertionParameter,
    Delta,
    Max,
    Min,
    Negate,
    NEGATE_DEFAULT,
    OptionalXmlInt,
    OutputBytes,
)
from ._util import _assert_number


def assert_has_size(
    output_bytes: OutputBytes,
    value: Annotated[OptionalXmlInt, AssertionParameter("Deprecated alias for `size`", xml_type="Bytes")] = None,
    size: Annotated[
        OptionalXmlInt,
        AssertionParameter(
            "Desired size of the output (in bytes), can be suffixed by ``(k|M|G|T|P|E)i?``", xml_type="Bytes"
        ),
    ] = None,
    delta: Delta = 0,
    min: Min = None,
    max: Max = None,
    negate: Negate = NEGATE_DEFAULT,
) -> None:
    """Asserts the specified output has a size of the specified value

    Attributes size and value or synonyms though value is considered deprecated.
    The size optionally allows for absolute (``delta``) difference.
    """
    output_size = len(output_bytes)
    if size is None:
        size = value
    _assert_number(
        output_size,
        value,
        delta,
        min,
        max,
        negate,
        "{expected} file size of {n}+-{delta}",
        "{expected} file size to be in [{min}:{max}]",
    )
