from collections import (
    Counter,
    namedtuple,
)

MockTransaction = namedtuple("MockTransaction", "user")


def have_same_elements(items, expected_items):
    """
    Assert that items and expected_items contain the same elements.
    """
    return Counter(items) == Counter(expected_items)
