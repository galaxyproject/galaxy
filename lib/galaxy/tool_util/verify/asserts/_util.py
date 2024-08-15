from math import inf
from typing import (
    Callable,
    Optional,
    TypeVar,
    Union,
)

from galaxy.util import asbool
from galaxy.util.bytesize import parse_bytesize


def _assert_number(
    count: int,
    n: Optional[Union[int, str]],
    delta: Union[int, str],
    min: Optional[Union[int, str]],
    max: Optional[Union[int, str]],
    negate: Union[bool, str],
    n_text: str,
    min_max_text: str,
) -> None:
    """
    helper function for assering that count is in
    - [n-delta:n+delta]
    - [min:max]

    raising an assertion error using n_text and min_max_text (resp)
    substituting {n}, {delta}, {min}, and {max}
    (and keeping potentially present {text} and {output})

    n, delta, min, max can be suffixed by (K|M|G|T|P|E)i?
    """
    negate = asbool(negate)
    expected = "Expected" if not negate else "Did not expect"
    if n is not None:
        n_bytes = parse_bytesize(n)
        delta_bytes = parse_bytesize(delta)
        assert (not negate) == (abs(count - n_bytes) <= delta_bytes), (
            n_text.format(expected=expected, n=n, delta=delta, text="{text}", output="{output}") + f" found {count}"
        )
    if min is not None or max is not None:
        if min is None:
            min = "-inf"  # also replacing min/max for output
            min_bytes = -inf
        else:
            min_bytes = parse_bytesize(min)
        if max is None:
            max = "inf"
            max_bytes = inf
        else:
            max_bytes = parse_bytesize(max)
        assert (not negate) == (min_bytes <= count <= max_bytes), (
            min_max_text.format(expected=expected, min=min, max=max, text="{text}", output="{output}")
            + f" found {count}"
        )


OutputType = TypeVar("OutputType")
TextType = TypeVar("TextType")


def _assert_presence_number(
    output: OutputType,
    text: TextType,
    n: Optional[Union[int, str]],
    delta: Union[int, str],
    min: Optional[Union[int, str]],
    max: Optional[Union[int, str]],
    negate: Union[bool, str],
    check_presence_foo: Callable[[OutputType, TextType], bool],
    count_foo: Callable[[OutputType, TextType], int],
    presence_text: str,
    n_text: str,
    min_max_text: str,
) -> None:
    """
    helper function to assert that
    - text is present in output using check_presence_foo
      this is done only if n, min, and max are None
    - text appears a certain number of times, where the count is determined with count foo

    raising an assertion error using presence_text, n_text or min_max_text (resp)
    substituting {n}, {delta}, {min}, {max}, {text}, and {output}

    n, delta, min, max can be suffixed by (K|M|G|T|P|E)i?
    """
    negate = asbool(negate)
    expected = "Expected" if not negate else "Did not expect"
    if n is None and min is None and max is None:
        assert (not negate) == check_presence_foo(output, text), presence_text.format(
            expected=expected, output=output, text=text
        )
    try:
        _assert_number(count_foo(output, text), n, delta, min, max, negate, n_text, min_max_text)
    except AssertionError as e:
        raise AssertionError(str(e).format(output=output, text=text))
