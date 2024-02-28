from collections import namedtuple

PRIVATE_OBJECT_STORE_ID = "my_private_data"

MockTransaction = namedtuple("MockTransaction", "user")


class MockObjectStore:

    def is_private(self, object):
        if object.object_store_id == PRIVATE_OBJECT_STORE_ID:
            return True
        else:
            return False


def verify_items(items1, length, items2=None):
    assert len(items1) == length
    if items2:
        assert set(items2) == set(i for i in items1)
