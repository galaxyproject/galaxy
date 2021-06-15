import re


def assert_has_text(output, text, n=None):
    """ Asserts specified output contains the substring specified by
    the argument text. The exact number of occurrences can be
    optionally specified by the argument n."""
    assert output is not None, "Checking has_text assertion on empty output (None)"
    if n is None:
        assert output.find(text) >= 0, f"Output file did not contain expected text '{text}' (output '{output}')"
    else:
        matches = re.findall(re.escape(text), output)
        assert len(matches) == int(n), f"Expected {n} matches for '{text}' in output file (output '{output}'); found {len(matches)}"


def assert_not_has_text(output, text):
    """ Asserts specified output does not contain the substring
    specified by the argument text."""
    assert output is not None, "Checking not_has_text assertion on empty output (None)"
    assert output.find(text) < 0, f"Output file contains unexpected text '{text}'"


def assert_has_line(output, line, n=None):
    """ Asserts the specified output contains the line specified by the
    argument line. The exact number of occurrences can be optionally
    specified by the argument n."""
    assert output is not None, "Checking has_line assertion on empty output (None)"
    if n is None:
        match = re.search(f"^{re.escape(line)}$", output, flags=re.MULTILINE)
        assert match is not None, f"No line of output file was '{line}' (output was '{output}') "
    else:
        matches = re.findall(f"^{re.escape(line)}$", output, flags=re.MULTILINE)
        assert len(matches) == int(n), f"Expected {n} lines matching '{line}' in output file (output was '{output}'); found {len(matches)}"


def assert_has_n_lines(output, n):
    """Asserts the specified output contains ``n`` lines."""
    assert output is not None, "Checking has_n_lines assertion on empty output (None)"
    n_lines_found = len(output.splitlines())
    assert n_lines_found == int(n), f"Expected {n} lines in output, found {n_lines_found} lines"


def assert_has_text_matching(output, expression):
    """ Asserts the specified output contains text matching the
    regular expression specified by the argument expression."""
    match = re.search(expression, output)
    assert match is not None, f"No text matching expression '{expression}' was found in output file."


def assert_has_line_matching(output, expression):
    """ Asserts the specified output contains a line matching the
    regular expression specified by the argument expression."""
    match = re.search(f"^{expression}$", output, flags=re.MULTILINE)
    assert match is not None, f"No line matching expression '{expression}' was found in output file."
