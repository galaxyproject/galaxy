"""
This file implements a brew resolver for Galaxy requirements. In order for Galaxy
to pick up on recursively defined and versioned brew dependencies recipes should
be installed using the experimental `brew-vinstall` external command.

More information here:

https://github.com/jmchilton/brew-tests
https://github.com/Homebrew/homebrew-science/issues/1191

This is still an experimental module and there will almost certainly be backward
incompatible changes coming.
"""


from .resolver_mixins import UsesHomebrewMixin
from ..resolvers import DependencyResolver, NullDependency

# TODO: Implement prefer version linked...
PREFER_VERSION_LINKED = 'linked'
PREFER_VERSION_LATEST = 'latest'
UNKNOWN_PREFER_VERSION_MESSAGE_TEMPLATE = "HomebrewDependencyResolver prefer_version must be %s"
UNKNOWN_PREFER_VERSION_MESSAGE = UNKNOWN_PREFER_VERSION_MESSAGE_TEMPLATE % (PREFER_VERSION_LATEST)
DEFAULT_PREFER_VERSION = PREFER_VERSION_LATEST


class HomebrewDependencyResolver(DependencyResolver, UsesHomebrewMixin):
    resolver_type = "homebrew"

    def __init__(self, dependency_manager, **kwds):
        self.versionless = _string_as_bool(kwds.get('versionless', 'false'))
        self.prefer_version = kwds.get('prefer_version', None)

        if self.prefer_version is None:
            self.prefer_version = DEFAULT_PREFER_VERSION

        if self.versionless and self.prefer_version not in [PREFER_VERSION_LATEST]:
            raise Exception(UNKNOWN_PREFER_VERSION_MESSAGE)

        self._init_homebrew(**kwds)

    def resolve(self, requirement, **kwds):
        name, version, type = requirement.name, requirement.version, requirement.type

        if type != "package":
            return NullDependency(version=version, name=name)

        if version is None or self.versionless:
            return self._find_dep_default(name, version)
        else:
            return self._find_dep_versioned(name, version)


def _string_as_bool( value ):
    return str( value ).lower() == "true"


__all__ = ('HomebrewDependencyResolver', )
