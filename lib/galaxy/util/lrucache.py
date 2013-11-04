"""
Kanwei Li, 03/2010

Simple LRU cache that uses a dictionary to store a specified number of objects
at a time.
"""

class LRUCache:
    def clear(self):
        ''' Clears/initiates storage variables'''
        self.key_ary = []
        self.obj_cache = {}

    def __init__(self, num_elements):
        self.num_elements = num_elements
        self.clear()

    def __getitem__(self, key):
        ''' Return value of key, or None if key is not in cache '''
        try:
            index = self.key_ary.index(key)
        except ValueError:
            return None
        # Move this key to the end
        self.key_ary.remove(key)
        self.key_ary.append(key)
        return self.obj_cache[key]

    def __setitem__(self, key, value):
        ''' Sets a new value to a key '''
        if key not in self.obj_cache:
            if len(self.key_ary) >= self.num_elements:
                deleted_key = self.key_ary.pop(0) # Remove first element
                del self.obj_cache[deleted_key]
            self.key_ary.append(key)
        self.obj_cache[key] = value
        return value

if __name__ == "__main__":
    import unittest

    class TestLRUCache(unittest.TestCase):
        def test_lru(self):
            lru = LRUCache(2)
            for i in range(0, 4): # Insert 4 numbers
                lru[i] = i
            self.assertEqual( lru[0], None )
            self.assertEqual( lru[1], None )
            self.assertEqual( lru[2], 2 )
            self.assertEqual( lru[3], 3 )

            self.assertEqual( lru.__setitem__("hello", "world"), "world")
            self.assertEqual( lru[2], None )

            lru.clear()
            self.assertEqual( lru["hello"], None )
            self.assertEqual( lru[3], None )

            # Test if recently used item is kept
            lru[0] = 0
            lru[1] = 1
            # Now saturated
            ping = lru[0]
            lru[2] = 2
            # Should keep 0, delete 1
            self.assertEqual( lru[0], 0 )
            self.assertEqual( lru[1], None )
            self.assertEqual( lru[2], 2 )

    unittest.main()

