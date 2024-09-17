"""
Ordered dictionary implementation with `insert` functionality.

This is only used in one specific place in the codebase:
    galaxy.tool_util.toolbox.panel

Whenever possible the stdlib `collections.OrderedDict` should be used instead of
this custom implementation.
"""

from collections import UserDict

dict_alias = dict


class odict(UserDict):
    """
    http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/107747

    This dictionary class extends UserDict to record the order in which items are
    added. Calling keys(), values(), items(), etc. will return results in this
    order.
    """

    def __init__(self, dict=None):
        item = dict
        self._keys = []
        if isinstance(item, dict_alias):
            UserDict.__init__(self, item)
        else:
            UserDict.__init__(self, None)
        if isinstance(item, list):
            for key, value in item:
                self[key] = value

    def __delitem__(self, key):
        UserDict.__delitem__(self, key)
        self._keys.remove(key)

    def __setitem__(self, key, item):
        UserDict.__setitem__(self, key, item)
        if key not in self._keys:
            self._keys.append(key)

    def clear(self):
        UserDict.clear(self)
        self._keys = []

    def copy(self):
        new = odict()
        new.update(self)
        return new

    def items(self):
        return zip(self._keys, self.values())

    def keys(self):
        return self._keys[:]

    def popitem(self):
        try:
            key = self._keys[-1]
        except IndexError:
            raise KeyError("dictionary is empty")
        val = self[key]
        del self[key]
        return (key, val)

    def setdefault(self, key, failobj=None):
        if key not in self._keys:
            self._keys.append(key)
        return UserDict.setdefault(self, key, failobj)

    def values(self):
        return map(self.get, self._keys)

    def iterkeys(self):
        return iter(self._keys)

    def itervalues(self):
        for key in self._keys:
            yield self.get(key)

    def iteritems(self):
        for key in self._keys:
            yield key, self.get(key)

    def __iter__(self):
        yield from self._keys

    def reverse(self):
        self._keys.reverse()

    def insert(self, index, key, item):
        if key not in self._keys:
            self._keys.insert(index, key)
            UserDict.__setitem__(self, key, item)
