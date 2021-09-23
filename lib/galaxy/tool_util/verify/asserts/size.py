def assert_has_size(output_bytes, value, delta=0, delta_frac=None):
    """
    Asserts the specified output has a size of the specified value,
    allowing for absolute (delta) and relative (delta_frac) difference.
    """
    output_size = len(output_bytes)
    value = int(value)
    delta = int(delta)
    assert abs(output_size - value) <= delta, f"Expected file size of {value}, actual file size is {output_size} (difference of {delta} accepted)"
    if delta_frac is not None:
        delta_frac = float(delta_frac)
        print(f'{value - (value * delta_frac)} {int(output_size)} {value + (value * delta_frac)}')
        assert (value - (value * delta_frac) <= int(output_size) <= value + (value * delta_frac)), f'Expected file size of {value}, actual file size is {output_size} (relative difference of {delta_frac} accepted, i.e. size in {value - (value * delta_frac)}:{value + (value * delta_frac)})'
