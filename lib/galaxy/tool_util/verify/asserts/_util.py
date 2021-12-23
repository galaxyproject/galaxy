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
