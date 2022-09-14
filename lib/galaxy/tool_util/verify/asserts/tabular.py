import re
from typing import Optional

from ._util import _assert_number


def get_first_line(output, comment):
    """
    get the first non-comment and non-empty line
    """
    if comment != "":
        match = re.search(f"^([^{comment}].*)$", output, flags=re.MULTILINE)
    else:
        match = re.search("^(.+)$", output, flags=re.MULTILINE)
    if match is None:
        return ""
    else:
        return match.group(1)


def assert_has_n_columns(
    output,
    n: Optional[int] = None,
    delta: int = 0,
    min: Optional[int] = None,
    max: Optional[int] = None,
    sep="\t",
    comment="",
    negate: bool = False,
):
    """Asserts the tabular output contains n columns. The optional
    sep argument specifies the column seperator used to determine the
    number of columns. The optional comment argument specifies
    comment characters"""
    first_line = get_first_line(output, comment)
    n_columns = len(first_line.split(sep))
    _assert_number(
        n_columns,
        n,
        delta,
        min,
        max,
        negate,
        "{expected} {n}+-{delta} columns in output",
        "{expected} the number of columns in output to be in [{min}:{max}]",
    )
