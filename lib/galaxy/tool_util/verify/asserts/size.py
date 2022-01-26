from ._util import _assert_number


def assert_has_size(output_bytes, value: str = None, delta: str = 0, min: str = None, max: str = None, negate: bool = False):
    """
    Asserts the specified output has a size of the specified value,
    allowing for absolute (delta) and relative (delta_frac) difference.
    """
    output_size = len(output_bytes)
    _assert_number(output_size, value, delta, min, max, negate,
        "{expected} file size of {n}+-{delta}",
        "{expected} file size to be in [{min}:{max}]")
