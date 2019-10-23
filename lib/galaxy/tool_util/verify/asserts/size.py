import sys
import io


def assert_has_size(output_bytes, value, delta=0):
    """Asserts the specified output has a size of the specified value"""
    output_temp = io.BytesIO(output_bytes)
    output_size = sys.getsizeof(output_temp)
    assert abs(output_size - int(value)) <= int(delta), "Expected file size was %s, actual file size was %s (difference of %s accepted)" % (value, output_size, delta)

