def assert_has_size(output_bytes, value: int, delta: int = 0, delta_frac: float = None):
    """
    Asserts the specified output has a size of the specified value,
    allowing for absolute (delta) and relative (delta_frac) difference.
    """
    output_size = len(output_bytes)
    value = int(value)
    delta = int(delta)
    assert abs(output_size - value) <= delta, f"Expected file size of {value}+-{delta}, actual file size is {output_size}"
    if delta_frac is not None:
        delta_frac = float(delta_frac)
        assert (value - (value * delta_frac) <= int(output_size) <= value + (value * delta_frac)), f"Expected file size of {value}+-{value * delta_frac}, actual file size is {output_size}"
