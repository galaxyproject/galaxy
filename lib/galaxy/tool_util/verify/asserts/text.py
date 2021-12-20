import re

from ._util import _assert_number


def _assert_presence_number(output, text, n, delta, min, max, check_presence_foo, count_foo, presence_text, n_text, min_max_text):
    """
    helper function to assert that
    - text is present in output using check_presence_foo
      this is done only if n, min, and max are None
    - text appears a certain number of times, where the count is determined with count foo

    raising an assertion error using presence_text, n_text or min_max_text (resp)
    substituting {n}, {delta}, {min}, {max}, {text}, and {output}
    """
    if n is None and min is None and max is None:
        assert check_presence_foo(output, text), presence_text.format(output=output, text=text)
    try:
        _assert_number(count_foo(output, text), n, delta, min, max, n_text, min_max_text)
    except AssertionError as e:
        raise AssertionError(str(e).format(output=output, text=text))


def assert_has_text(output, text, n: int = None, delta: int = 0, min: int = None, max: int = None):
    """ Asserts specified output contains the substring specified by
    the argument text. The exact number of occurrences can be
    optionally specified by the argument n"""
    assert output is not None, "Checking has_text assertion on empty output (None)"
    _assert_presence_number(output, text, n, delta, min, max,
        lambda o, t: o.find(t) >= 0,
        lambda o, t: len(re.findall(re.escape(t), o)),
        "Output file did not contain expected text '{text}' (output '{output}')",
        "Expected {n}+-{delta} occurences of '{text}' in output file (output '{output}')",
        "Expected that the number of occurences of '{text}' in output file is in [{min}:{max}] (output '{output}')")


def assert_not_has_text(output, text):
    """ Asserts specified output does not contain the substring
    specified by the argument text"""
    assert output is not None, "Checking not_has_text assertion on empty output (None)"
    assert output.find(text) < 0, f"Output file contains unexpected text '{text}'"


def assert_has_line(output, line, n: int = None, delta: int = 0, min: int = None, max: int = None):
    """ Asserts the specified output contains the line specified by the
    argument line. The exact number of occurrences can be optionally
    specified by the argument n"""
    assert output is not None, "Checking has_line assertion on empty output (None)"
    _assert_presence_number(output, line, n, delta, min, max,
        lambda o, l: re.search(f"^{re.escape(l)}$", o, flags=re.MULTILINE) is not None,
        lambda o, l: len(re.findall(f"^{re.escape(l)}$", o, flags=re.MULTILINE)),
        "No line of output file was '{text}' (output was '{output}')",
        "Expected {n}+-{delta} lines '{text}' in output file (output was '{output}')",
        "Expected that the number of lines '{text}' in output file is in [{min}:{max}] (output '{output}')")


def assert_has_n_lines(output, n: int = None, delta: int = 0, min: int = None, max: int = None):
    """Asserts the specified output contains ``n`` lines allowing
    for a difference in the number of lines (delta)
    or relative differebce in the number of lines"""
    assert output is not None, "Checking has_n_lines assertion on empty output (None)"
    count = len(output.splitlines())
    _assert_number(count, n, delta, min, max,
        "Expected {n}+-{delta} lines in the output",
        "Expected the number of line to be in [{min}:{max}]")


def assert_has_text_matching(output, expression, n: int = None, delta: int = 0, min: int = None, max: int = None):
    """ Asserts the specified output contains text matching the
    regular expression specified by the argument expression.
    If n is given the assertion checks for exacly n (nonoverlapping)
    occurences.
    """
    _assert_presence_number(output, expression, n, delta, min, max,
        lambda o, e: re.search(e, o) is not None,
        lambda o, e: len(re.findall(e, o)),
        "No text matching expression '{text}' was found in output file (output '{output}')",
        "Expected {n}+-{delta} (non-overlapping) matches for '{text}' in output file (output '{output}')",
        "Expected that the number of (non-overlapping) matches for '{text}' in output file is in [{min}:{max}] (output '{output}')")


def assert_has_line_matching(output, expression, n: int = None, delta: int = 0, min: int = None, max: int = None):
    """ Asserts the specified output contains a line matching the
    regular expression specified by the argument expression. If n is given
    the assertion checks for exactly n occurences."""
    _assert_presence_number(output, expression, n, delta, min, max,
        lambda o, e: re.search(f"^{e}$", o, flags=re.MULTILINE) is not None,
        lambda o, e: len(re.findall(f"^{e}$", o, flags=re.MULTILINE)),
        "No line matching expression '{text}' was found in output file (output '{output}')",
        "Expected {n}+-{delta} lines matching for '{text}' in output file (output '{output}')",
        "Expected that the number of lines matching for '{text}' in output file is in [{min}:{max}] (output '{output}')")
