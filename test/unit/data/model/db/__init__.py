from collections import (
    Counter,
    namedtuple,
)

MockTransaction = namedtuple("MockTransaction", "user")


def verify_items(items, expected_items):
    """
    Assert that items and expected_items contain the same elements.
    """
    assert Counter(items) == Counter(expected_items)
