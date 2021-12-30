from math import inf

from galaxy.util import asbool


def _assert_number(count, n, delta, min, max, negate, n_text, min_max_text):
    """
    helper function for assering that count is in
    - n +- delta
    - min:max

    raising an assertion error using n_text and min_max_text (resp)
    substituting {n}, {delta}, {min}, and {max}
    (and keeping potentially present {text} and {output})
    """
    negate = asbool(negate)
    expected = "Expected" if not negate else "Did not expect"
    if n is not None:
        assert (not negate) == (abs(count - int(n)) <= int(delta)), n_text.format(expected=expected, n=n, delta=delta, text="{text}", output="{output}") + f" found {count}"
    if min is not None or max is not None:
        if min is None:
            min = -inf
        else:
            min = int(min)
        if max is None:
            max = inf
        else:
            max = int(max)
        assert (not negate) == (min <= count <= max), min_max_text.format(expected=expected, min=min, max=max, text="{text}", output="{output}") + f" found {count}"


def _assert_presence_number(output, text, n, delta, min, max, negate, check_presence_foo, count_foo, presence_text, n_text, min_max_text):
    """
    helper function to assert that
    - text is present in output using check_presence_foo
      this is done only if n, min, and max are None
    - text appears a certain number of times, where the count is determined with count foo

    raising an assertion error using presence_text, n_text or min_max_text (resp)
    substituting {n}, {delta}, {min}, {max}, {text}, and {output}
    """
    print(f"{text} {output} eval {check_presence_foo(output, text)}")
    negate = asbool(negate)
    expected = "Expected" if not negate else "Did not expect"
    if n is None and min is None and max is None:
        print(f"negate {negate} presence {check_presence_foo(output, text)}")
        assert (not negate) == check_presence_foo(output, text), presence_text.format(expected=expected, output=output, text=text)
    try:
        _assert_number(count_foo(output, text), n, delta, min, max, negate, n_text, min_max_text)
    except AssertionError as e:
        raise AssertionError(str(e).format(output=output, text=text))
