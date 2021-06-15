def assert_has_size(output_bytes, value, delta=0):
    """Asserts the specified output has a size of the specified value"""
    output_size = len(output_bytes)
    assert abs(output_size - int(value)) <= int(delta), f"Expected file size was {value}, actual file size was {output_size} (difference of {delta} accepted)"
