import sys
import io

def assert_has_line(output, line):
    """ Asserts the specified output contains the line specified the
    argument line."""
    match = re.search("^%s$" % re.escape(line), output, flags=re.MULTILINE)
    assert match is not None, "No line of output file was '%s' (output was '%s') " % (line, output)


def assert_has_size(output_bytes, value):
    """Asserts the specified output has a size of the specified value"""
    
    output_temp = io.BytesIO(output_bytes)
    output_size = sys.getsizeof(output_temp)
    assert output_size == value, "Expected file size was %s, actual file size was" % (value, output_size)

