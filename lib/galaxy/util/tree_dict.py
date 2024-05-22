from collections import UserDict
from collections.abc import (
    ItemsView,
    MutableMapping,
)
from typing import (
    Any,
    Optional,
)

from boltons.iterutils import remap


def enter(path, key, value):
    if isinstance(value, MutableMapping):
        return value.__class__(), ItemsView(value)
    else:
        return value, False


class TreeDict(UserDict):
    """
    Dictionary that inserts its own keys in a parent dictionary.
    """

    def __init__(self, dict=None, **kwargs):
        self._parent_data: Optional[TreeDict] = None
        self._injected_data = {}
        super().__init__(dict, **kwargs)

    def clean_copy(self):
        """
        Copy without injected data.
        """

        def strip_tree_dict(path, key, value):
            if isinstance(value, TreeDict):
                value = value.data
            return key, value

        return remap(self.data, strip_tree_dict, enter=enter)

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
        current_parent_data = self._parent_data
        while current_parent_data is not None and key != "__current_case__":
            if (
                key not in current_parent_data
                or key == "input"
                and key in current_parent_data
                and callable(current_parent_data[key])
            ):
                current_parent_data._injected_data[key] = item
            current_parent_data = current_parent_data._parent_data
        return super().__setitem__(key, item)
