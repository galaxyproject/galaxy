from decimal import Decimal

import pytest

from galaxy.util.json import (
    safe_dumps,
    swap_inf_nan,
)


@pytest.mark.parametrize(
    "val,expected_val",
    [
        (float("inf"), "__Infinity__"),
        (float("-inf"), "__-Infinity__"),
        (float("NaN"), "__NaN__"),
        (Decimal("1"), "1"),
    ],
)
def test_swap_inf_nan(val, expected_val):
    assert swap_inf_nan(val) == expected_val


def test_safe_dumps():
    assert safe_dumps({"a": Decimal("0.1")}) == """{"a": "0.1"}"""
