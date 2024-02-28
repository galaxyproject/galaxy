from collections import (
    Counter,
    namedtuple,
)

PRIVATE_OBJECT_STORE_ID = "my_private_data"

MockTransaction = namedtuple("MockTransaction", "user")


class MockObjectStore:

    def is_private(self, object):
        if object.object_store_id == PRIVATE_OBJECT_STORE_ID:
            return True
        else:
            return False


def verify_items(items, expected_items):
    """
    Assert that items and expected_items contain the same elements.
    """
    assert Counter(items) == Counter(expected_items)
