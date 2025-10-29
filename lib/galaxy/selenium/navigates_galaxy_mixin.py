"""Parent class for mixins that are meant to extend NavigatesGalaxy.

This provides some level of type checking support despite being a bit hacky.
"""

from typing import TYPE_CHECKING

from .navigates_galaxy import NavigatesGalaxy

if TYPE_CHECKING:
    NavigatesGalaxyMixin = NavigatesGalaxy
else:
    NavigatesGalaxyMixin = object

__all__ = ("NavigatesGalaxyMixin",)
