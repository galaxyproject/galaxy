from collections import UserDict
from collections.abc import MutableMapping
from typing import (
    Any,
    Optional,
)


class TreeDict(UserDict):
    """
    Dictionary that inserts its own keys in a parent dictionary.
    """

    def __init__(self, dict=None, **kwargs):
        self._parent_data: Optional[TreeDict] = None
        self._injected_data = {}
        super().__init__(dict, **kwargs)

    def __getitem__(self, key: Any) -> Any:
        if key in self.data:
            return super().__getitem__(key)
        else:
            return self._injected_data[key]

    def __contains__(self, key: object) -> bool:
        if super().__contains__(key):
            return True
        return key in self._injected_data

    def __setitem__(self, key: Any, item: Any) -> None:
        if isinstance(item, MutableMapping):
            # We're not doing item = TreeDict(item) because we want to record the keys in _parent_data
            _item = TreeDict()
            _item._parent_data = self
            _item.update(item)
            item = _item
        if self._parent_data is not None and key != "__current_case__":
            if (
                key not in self._parent_data
                or key == "input"
                and key in self._parent_data
                and callable(self._parent_data[key])
            ):
                self._parent_data._injected_data[key] = item
        return super().__setitem__(key, item)
