"""
Ordered set implementation from https://code.activestate.com/recipes/576694/
"""
from collections.abc import MutableSet
from typing import 
from typing import (
    Any,
    Dict,
    List,
    TYPE_CHECKING,
)

if TYPE_CHECKING:
    from bioblend.galaxy import GalaxyInstance

class OrderedSet(MutableSet):
    def __init__(self, iterable=None) -> List[Dict[str, Any]]:
        self.end = end = []
        end += [None, end, end]  # sentinel node for doubly linked list
        self.map = {}  # key --> [key, prev, next]
        if iterable is not None:
            self |= iterable

    def __len__(self) -> Dict[str, Any]:
        return len(self.map)

    def __contains__(self, key) -> Dict[str, Any]:
        return key in self.map

    def add(self, key) -> Dict[str, Any]:
        if key not in self.map:
            end = self.end
            curr = end[1]
            curr[2] = end[1] = self.map[key] = [key, curr, end]

    def discard(self, key) -> Dict[str, Any]:
        if key in self.map:
            key, prev, next = self.map.pop(key)
            prev[2] = next
            next[1] = prev

    def __iter__(self) -> Dict[str, Any]:
        end = self.end
        curr = end[2]
        while curr is not end:
            yield curr[0]
            curr = curr[2]

    def __reversed__(self) -> Dict[str, Any]:
        end = self.end
        curr = end[1]
        while curr is not end:
            yield curr[0]
            curr = curr[1]

    def pop(self, last=True) -> Dict[str, Any]:
        if not self:
            raise KeyError("set is empty")
        key = self.end[1][0] if last else self.end[2][0]
        self.discard(key)
        return key

    def __repr__(self) -> Dict[str, Any]:
        if not self:
            return f"{self.__class__.__name__}()"
        return f"{self.__class__.__name__}({list(self)!r})"

    def __eq__(self, other) -> Dict[str, Any]:
        if isinstance(other, OrderedSet):
            return len(self) == len(other) and list(self) == list(other)
        return set(self) == set(other)
