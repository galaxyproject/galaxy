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

import os

from ..brew_exts import DEFAULT_HOMEBREW_ROOT, recipe_cellar_path, build_env_statements
from ..resolvers import DependencyResolver, INDETERMINATE_DEPENDENCY, Dependency

# TODO: Implement prefer version linked...
PREFER_VERSION_LINKED = 'linked'
PREFER_VERSION_LATEST = 'latest'
UNKNOWN_PREFER_VERSION_MESSAGE_TEMPLATE = "HomebrewDependencyResolver prefer_version must be latest %s"
UNKNOWN_PREFER_VERSION_MESSAGE = UNKNOWN_PREFER_VERSION_MESSAGE_TEMPLATE % (PREFER_VERSION_LATEST)
DEFAULT_PREFER_VERSION = PREFER_VERSION_LATEST


class HomebrewDependencyResolver(DependencyResolver):
    resolver_type = "homebrew"

    def __init__(self, dependency_manager, **kwds):
        self.versionless = _string_as_bool(kwds.get('versionless', 'false'))
        self.prefer_version = kwds.get('prefer_version', None)

        if self.prefer_version is None:
            self.prefer_version = DEFAULT_PREFER_VERSION

        if self.versionless and self.prefer_version not in [PREFER_VERSION_LATEST]:
            raise Exception(UNKNOWN_PREFER_VERSION_MESSAGE)

        cellar_root = kwds.get('cellar', None)
        if cellar_root is None:
            cellar_root = os.path.join(DEFAULT_HOMEBREW_ROOT, "Cellar")

        self.cellar_root = cellar_root

    def resolve(self, name, version, type, **kwds):
        if type != "package":
            return INDETERMINATE_DEPENDENCY

        if version is None or self.versionless:
            return self._find_dep_default(name, version)
        else:
            return self._find_dep_versioned(name, version)

    def _find_dep_versioned(self, name, version):
        recipe_path = recipe_cellar_path(self.cellar_root, name, version)
        if not os.path.exists(recipe_path) or not os.path.isdir(recipe_path):
            return INDETERMINATE_DEPENDENCY

        commands = build_env_statements(self.cellar_root, recipe_path, relaxed=True)
        return HomebrewDependency(commands)

    def _find_dep_default(self, name, version):
        installed_versions = self._installed_versions(name)
        if not installed_versions:
            return INDETERMINATE_DEPENDENCY

        # Just grab newest installed version - may make sense some day to find
        # the linked version instead.
        default_version = sorted(installed_versions, reverse=True)[0]
        return self._find_dep_versioned(name, default_version)

    def _installed_versions(self, recipe):
        recipe_base_path = os.path.join(self.cellar_root, recipe)
        if not os.path.exists(recipe_base_path):
            return []

        names = os.listdir(recipe_base_path)
        return filter(lambda n: os.path.isdir(os.path.join(recipe_base_path, n)), names)


class HomebrewDependency(Dependency):

    def __init__(self, commands):
        self.commands = commands

    def shell_commands(self, requirement):
        return self.commands.replace("\n", ";") + "\n"


def _string_as_bool( value ):
    return str( value ).lower() == "true"


__all__ = [HomebrewDependencyResolver]
