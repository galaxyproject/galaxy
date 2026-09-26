from packaging.version import Version

from .version import LegacyVersion

AnyVersionT = LegacyVersion | Version


__all__ = ["AnyVersionT"]
