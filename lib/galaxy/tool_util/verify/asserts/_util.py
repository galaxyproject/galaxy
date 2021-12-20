from math import inf


def _assert_number(count, n, delta, min, max, n_text, min_max_text):
    """
    helper function for assering that count is in
    - n +- delta
    - min:max

    raising an assertion error using n_text and min_max_text (resp)
    substituting {n}, {delta}, {min}, and {max}
    (and keeping potentially present {text} and {output})
    """
    if n is not None:
        assert abs(count - int(n)) <= int(delta), n_text.format(n=n, delta=delta, text="{text}", output="{output}") + f" found {count}"
    if min is not None or max is not None:
        if min is None:
            min = -inf
        else:
            min = int(min)
        if max is None:
            max = inf
        else:
            max = int(max)
        assert min <= count <= max, min_max_text.format(min=min, max=max, text="{text}", output="{output}") + f" found {count}"
