"""
Ordered dictionary implementation with `insert` functionality.

This is only used in one specific place in the codebase:
    galaxy.tool_util.toolbox.panel

Whenever possible the stdlib `collections.OrderedDict` should be used instead of
this custom implementation.
"""

import sys
from collections import UserDict
from typing import (
    Dict,
    Generic,
    List,
    Optional,
    Tuple,
    TypeVar,
    Union,
)

dict_alias = dict

KeyT = TypeVar("KeyT")
ValueT = TypeVar("ValueT")

if sys.version_info >= (3, 9):

    # A simple type alias doesn't work with mypy
    class TypedUserDict(UserDict[KeyT, ValueT]): ...

else:

    # UserDict is not generic in Python < 3.9
    # TypeError: 'ABCMeta' object is not subscriptable
    class TypedUserDict(UserDict, Generic[KeyT, ValueT]): ...


class odict(TypedUserDict[KeyT, ValueT]):
    """
    http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/107747

    This dictionary class extends UserDict to record the order in which items are
    added. Calling keys(), values(), items(), etc. will return results in this
    order.
    """

    def __init__(self, dict: Optional[Union[Dict[KeyT, ValueT], List[Tuple[KeyT, ValueT]]]] = None) -> None:
        item = dict
        self._keys: List[KeyT] = []
        if isinstance(item, dict_alias):
            super().__init__(item)
        else:
            super().__init__(None)
        if isinstance(item, list):
            for key, value in item:
                self[key] = value

    def __delitem__(self, key: KeyT) -> None:
        super().__delitem__(key)
        self._keys.remove(key)

    def __setitem__(self, key: KeyT, item: ValueT) -> None:
        super().__setitem__(key, item)
        if key not in self._keys:
            self._keys.append(key)

    def clear(self) -> None:
        super().clear()
        self._keys = []

    def copy(self) -> "odict[KeyT, ValueT]":
        new: odict[KeyT, ValueT] = odict()
        new.update(self)
        return new

    def items(self):
        return zip(self._keys, self.values())

    def keys(self):
        return self._keys[:]

    def popitem(self) -> Tuple[KeyT, ValueT]:
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
        return super().setdefault(key, failobj)

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

    def insert(self, index, key: KeyT, item: ValueT) -> None:
        if key not in self._keys:
            self._keys.insert(index, key)
            super().__setitem__(key, item)
