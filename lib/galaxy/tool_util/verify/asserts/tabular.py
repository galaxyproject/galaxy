import re

from ._types import (
    Annotated,
    AssertionParameter,
    Delta,
    Max,
    Min,
    N,
    Negate,
    NEGATE_DEFAULT,
    Output,
)
from ._util import _assert_number

Sep = Annotated[str, AssertionParameter("Separator defining columns, default: tab")]
Comment = Annotated[
    str,
    AssertionParameter(
        "Comment character(s) used to skip comment lines (which should not be used for counting columns)"
    ),
]


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
    output: Output,
    n: N = None,
    delta: Delta = 0,
    min: Min = None,
    max: Max = None,
    sep: Sep = "\t",
    comment: Comment = "",
    negate: Negate = NEGATE_DEFAULT,
) -> None:
    """Asserts tabular output  contains the specified
    number (``n``) of columns.

    For instance, ``<has_n_columns n="3"/>``. The assertion tests only the first line.
    Number of columns can optionally also be specified with ``delta``. Alternatively the
    range of expected occurences can be specified by ``min`` and/or ``max``.

    Optionally a column separator (``sep``, default is ``\t``) `and comment character(s)
    can be specified (``comment``, default is empty string). The first non-comment
    line is used for determining the number of columns.
    """
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
