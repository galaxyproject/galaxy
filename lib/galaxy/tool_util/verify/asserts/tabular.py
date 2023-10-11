import re
from typing import (
    Optional,
    Union,
)

from ._util import _assert_number


def get_first_line(output: str, comment: str) -> str:
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
    output: str,
    n: Optional[Union[int, str]] = None,
    delta: Union[int, str] = 0,
    min: Optional[Union[int, str]] = None,
    max: Optional[Union[int, str]] = None,
    sep: str = "\t",
    comment: str = "",
    negate: Union[bool, str] = False,
) -> None:
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
