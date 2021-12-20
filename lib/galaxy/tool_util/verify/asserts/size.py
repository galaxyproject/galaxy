from ._util import _assert_number


def assert_has_size(output_bytes, value: int = None, delta: int = 0, min: int = None, max: int = None):
    """
    Asserts the specified output has a size of the specified value,
    allowing for absolute (delta) and relative (delta_frac) difference.
    """
    output_size = len(output_bytes)
    _assert_number(output_size, value, delta, min, max,
        "Expected file size of {n}+-{delta}",
        "Expected file size to be in [{min}:{max}]")
