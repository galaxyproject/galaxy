import re
from typing import Optional

from ._util import (
    _assert_number,
    _assert_presence_number,
)


def assert_has_text(
    output,
    text,
    n: Optional[int] = None,
    delta: int = 0,
    min: Optional[int] = None,
    max: Optional[int] = None,
    negate: bool = False,
):
    """Asserts specified output contains the substring specified by
    the argument text. The exact number of occurrences can be
    optionally specified by the argument n"""
    assert output is not None, "Checking has_text assertion on empty output (None)"
    _assert_presence_number(
        output,
        text,
        n,
        delta,
        min,
        max,
        negate,
        lambda o, t: o.find(t) >= 0,
        lambda o, t: len(re.findall(re.escape(t), o)),
        "{expected} text '{text}' in output ('{output}')",
        "{expected} {n}+-{delta} occurences of '{text}' in output ('{output}')",
        "{expected} that the number of occurences of '{text}' in output is in [{min}:{max}] ('{output}')",
    )


def assert_not_has_text(output, text):
    """Asserts specified output does not contain the substring
    specified by the argument text"""
    assert output is not None, "Checking not_has_text assertion on empty output (None)"
    assert output.find(text) < 0, f"Output file contains unexpected text '{text}'"


def assert_has_line(
    output,
    line,
    n: Optional[int] = None,
    delta: int = 0,
    min: Optional[int] = None,
    max: Optional[int] = None,
    negate: bool = False,
):
    """Asserts the specified output contains the line specified by the
    argument line. The exact number of occurrences can be optionally
    specified by the argument n"""
    assert output is not None, "Checking has_line assertion on empty output (None)"
    _assert_presence_number(
        output,
        line,
        n,
        delta,
        min,
        max,
        negate,
        lambda o, l: re.search(f"^{re.escape(l)}$", o, flags=re.MULTILINE) is not None,
        lambda o, l: len(re.findall(f"^{re.escape(l)}$", o, flags=re.MULTILINE)),
        "{expected} line '{text}' in output ('{output}')",
        "{expected} {n}+-{delta} lines '{text}' in output ('{output}')",
        "{expected} that the number of lines '{text}' in output is in [{min}:{max}] ('{output}')",
    )


def assert_has_n_lines(
    output,
    n: Optional[int] = None,
    delta: int = 0,
    min: Optional[int] = None,
    max: Optional[int] = None,
    negate: bool = False,
):
    """Asserts the specified output contains ``n`` lines allowing
    for a difference in the number of lines (delta)
    or relative differebce in the number of lines"""
    assert output is not None, "Checking has_n_lines assertion on empty output (None)"
    count = len(output.splitlines())
    _assert_number(
        count,
        n,
        delta,
        min,
        max,
        negate,
        "{expected} {n}+-{delta} lines in the output",
        "{expected} the number of line to be in [{min}:{max}]",
    )


def assert_has_text_matching(
    output,
    expression,
    n: Optional[int] = None,
    delta: int = 0,
    min: Optional[int] = None,
    max: Optional[int] = None,
    negate: bool = False,
):
    """Asserts the specified output contains text matching the
    regular expression specified by the argument expression.
    If n is given the assertion checks for exacly n (nonoverlapping)
    occurences.
    """
    _assert_presence_number(
        output,
        expression,
        n,
        delta,
        min,
        max,
        negate,
        lambda o, e: re.search(e, o) is not None,
        lambda o, e: len(re.findall(e, o)),
        "{expected} text matching expression '{text}' in output ('{output}')",
        "{expected} {n}+-{delta} (non-overlapping) matches for '{text}' in output ('{output}')",
        "{expected} that the number of (non-overlapping) matches for '{text}' in output is in [{min}:{max}] ('{output}')",
    )


def assert_has_line_matching(
    output,
    expression,
    n: Optional[int] = None,
    delta: int = 0,
    min: Optional[int] = None,
    max: Optional[int] = None,
    negate: bool = False,
):
    """Asserts the specified output contains a line matching the
    regular expression specified by the argument expression. If n is given
    the assertion checks for exactly n occurences."""
    _assert_presence_number(
        output,
        expression,
        n,
        delta,
        min,
        max,
        negate,
        lambda o, e: re.search(f"^{e}$", o, flags=re.MULTILINE) is not None,
        lambda o, e: len(re.findall(f"^{e}$", o, flags=re.MULTILINE)),
        "{expected} line matching expression '{text}' in output ('{output}')",
        "{expected} {n}+-{delta} lines matching for '{text}' in output ('{output}')",
        "{expected} that the number of lines matching for '{text}' in output is in [{min}:{max}] ('{output}')",
    )
