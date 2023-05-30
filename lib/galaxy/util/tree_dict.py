from collections import UserDict
from typing import Any


class TreeDict(UserDict):
    """
    Dictionary that inserts its own keys in a parent dictionary.
    """

    def __init__(self, dict=None, **kwargs):
        self._parent_data = None
        self._child_data = {}
        super().__init__(dict, **kwargs)

    def __setitem__(self, key: Any, item: Any) -> None:
        if isinstance(item, dict):
            d = TreeDict()
            d._parent_data = self
            d.update(item)
            item = d
        if self._parent_data is not None:
            if key not in self._parent_data:
                self._parent_data[key] = item
        return super().__setitem__(key, item)
