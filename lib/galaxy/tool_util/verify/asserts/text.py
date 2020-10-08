import re


def assert_has_text(output, text, n=None):
    """ Asserts specified output contains the substring specified by
    the argument text. The exact number of occurrences can be
    optionally specified by the argument n."""
    if n is None:
        assert output.find(text) >= 0, f"Output file did not contain expected text '{text}' (output '{output}')"
    else:
        matches = re.findall(re.escape(text), output)
        assert len(matches) == int(n), "Expected {} matches for '{}' in output file (output '{}'); found {}".format(n, text, output, len(matches))


def assert_not_has_text(output, text):
    """ Asserts specified output does not contain the substring
    specified by the argument text."""
    assert output.find(text) < 0, "Output file contains unexpected text '%s'" % text


def assert_has_line(output, line, n=None):
    """ Asserts the specified output contains the line specified by the
    argument line. The exact number of occurrences can be optionally
    specified by the argument n."""
    if n is None:
        match = re.search("^%s$" % re.escape(line), output, flags=re.MULTILINE)
        assert match is not None, f"No line of output file was '{line}' (output was '{output}') "
    else:
        matches = re.findall("^%s$" % re.escape(line), output, flags=re.MULTILINE)
        assert len(matches) == int(n), "Expected {} lines matching '{}' in output file (output was '{}'); found {}".format(n, line, output, len(matches))


def assert_has_n_lines(output, n):
    """Asserts the specified output contains ``n`` lines."""
    n_lines_found = len(output.splitlines())
    assert n_lines_found == int(n), f"Expected {n} lines in output, found {n_lines_found} lines"


def assert_has_text_matching(output, expression):
    """ Asserts the specified output contains text matching the
    regular expression specified by the argument expression."""
    match = re.search(expression, output)
    assert match is not None, "No text matching expression '%s' was found in output file." % expression


def assert_has_line_matching(output, expression):
    """ Asserts the specified output contains a line matching the
    regular expression specified by the argument expression."""
    match = re.search("^%s$" % expression, output, flags=re.MULTILINE)
    assert match is not None, "No line matching expression '%s' was found in output file." % expression
