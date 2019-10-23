def assert_has_size(output_bytes, value, delta=0):
    """Asserts the specified output has a size of the specified value"""
    output_size = len(output_bytes)
    assert abs(output_size - int(value)) <= int(delta), "Expected file size was %s, actual file size was %s (difference of %s accepted)" % (value, output_size, delta)
