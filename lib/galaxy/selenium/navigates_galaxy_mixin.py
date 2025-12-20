"""Parent class for mixins that are meant to extend NavigatesGalaxy.

This provides some level of type checking support despite being a bit hacky.
"""

from typing import TYPE_CHECKING

from .context import GalaxySeleniumContext

if TYPE_CHECKING:
    NavigatesGalaxyMixin = GalaxySeleniumContext
else:
    NavigatesGalaxyMixin = object

__all__ = ("NavigatesGalaxyMixin",)
