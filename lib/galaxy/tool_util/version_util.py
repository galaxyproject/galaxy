from typing import Union

from packaging.version import Version

from .version import LegacyVersion

AnyVersionT = Union[LegacyVersion, Version]


__all__ = ["AnyVersionT"]
