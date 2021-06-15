"""
Expression evaluation support.

For the moment this depends on python's eval. In the future it should be
replaced with a "safe" parser.
"""

from collections.abc import MutableMapping
from itertools import chain


class ExpressionContext(MutableMapping):
    def __init__(self, dict, parent=None):
        """
        Create a new expression context that looks for values in the
        container object 'dict', and falls back to 'parent'
        """
        self.dict = dict
        self.parent = parent

    def __delitem__(self, key):
        if key in self.dict:
            del self.dict[key]
        elif self.parent is not None and key in self.parent:
            del self.parent[key]

    def __iter__(self):
        return chain(iter(self.dict), iter(self.parent or []))

    def __len__(self):
        return len(self.dict) + len(self.parent or [])

    def __getitem__(self, key):
        if key in self.dict:
            return self.dict[key]
        if self.parent is not None and key in self.parent:
            return self.parent[key]
        raise KeyError(key)

    def __setitem__(self, key, value):
        self.dict[key] = value

    def __contains__(self, key):
        if key in self.dict:
            return True
        if self.parent is not None and key in self.parent:
            return True
        return False

    def __str__(self):
        return str(self.dict)

    def __bool__(self):
        if not self.dict and not self.parent:
            return False
        return True
    __nonzero__ = __bool__
