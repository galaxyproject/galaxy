from collections.abc import (
    ItemsView,
    Iterator,
    KeysView,
    ValuesView,
)
from typing import Any

from .dynamic import HasDynamicProperties


class Bunch(HasDynamicProperties):
    """
    http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/52308

    Often we want to just collect a bunch of stuff together, naming each item of
    the bunch; a dictionary's OK for that, but a small do-nothing class is even handier, and prettier to use.

    For new code, use dataclasses from the standard library instead.
    """

    def __init__(self, **kwds: Any) -> None:
        self.__dict__.update(kwds)

    def dict(self) -> dict[str, Any]:
        return self.__dict__

    def get(self, key: str, default: Any = None) -> Any:
        return self.__dict__.get(key, default)

    def __iter__(self) -> Iterator[str]:
        return iter(self.__dict__)

    def items(self) -> ItemsView[str, Any]:
        return self.__dict__.items()

    def keys(self) -> KeysView[str]:
        return self.__dict__.keys()

    def values(self) -> ValuesView[Any]:
        return self.__dict__.values()

    def __str__(self) -> str:
        return f"{self.__dict__}"

    def __bool__(self) -> bool:
        return bool(self.__dict__)

    __nonzero__ = __bool__

    def __setitem__(self, k: str, v: Any) -> None:
        self.__dict__.__setitem__(k, v)

    def __contains__(self, item: object) -> bool:
        return item in self.__dict__
