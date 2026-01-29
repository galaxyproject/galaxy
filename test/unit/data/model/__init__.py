PRIVATE_OBJECT_STORE_ID = "my_private_data"


class MockObjectStore:

    def is_private(self, object):
        if object.object_store_id == PRIVATE_OBJECT_STORE_ID:
            return True
        else:
            return False
