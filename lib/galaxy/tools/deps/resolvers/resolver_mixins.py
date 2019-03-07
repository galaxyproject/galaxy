import os

from . import (
    Dependency,
    NullDependency
)
from ..brew_exts import (
    build_env_statements,
    DEFAULT_HOMEBREW_ROOT,
    recipe_cellar_path,
)


class UsesHomebrewMixin(object):

    def _init_homebrew(self, **kwds):
        cellar_root = kwds.get('cellar', None)
        if cellar_root is None:
            cellar_root = os.path.join(DEFAULT_HOMEBREW_ROOT, "Cellar")

        self.cellar_root = cellar_root

    def _find_dep_versioned(self, name, version):
        recipe_path = recipe_cellar_path(self.cellar_root, name, version)
        if not os.path.exists(recipe_path) or not os.path.isdir(recipe_path):
            return NullDependency(version=version, name=name)

        commands = build_env_statements(self.cellar_root, recipe_path, relaxed=True)
        return HomebrewDependency(commands)

    def _find_dep_default(self, name, version):
        installed_versions = self._installed_versions(name)
        if not installed_versions:
            return NullDependency(version=version, name=name)

        # Just grab newest installed version - may make sense some day to find
        # the linked version instead.
        default_version = sorted(installed_versions, reverse=True)[0]
        return self._find_dep_versioned(name, default_version, exact=version is None)

    def _installed_versions(self, recipe):
        recipe_base_path = os.path.join(self.cellar_root, recipe)
        if not os.path.exists(recipe_base_path):
            return []

        names = os.listdir(recipe_base_path)
        return [n for n in names if os.path.isdir(os.path.join(recipe_base_path, n))]


class UsesToolDependencyDirMixin(object):

    def _init_base_path(self, dependency_manager, **kwds):
        self.base_path = os.path.abspath(kwds.get('base_path', dependency_manager.default_base_path))


class UsesInstalledRepositoriesMixin(object):

    def _get_installed_dependency(self, name, type, version=None, **kwds):
        installed_tool_dependencies = kwds.get("installed_tool_dependencies") or []
        for installed_tool_dependency in installed_tool_dependencies:
            if installed_tool_dependency.name == name and installed_tool_dependency.type == type:
                if not version or installed_tool_dependency.version == version:
                    return installed_tool_dependency
        return None


class HomebrewDependency(Dependency):

    def __init__(self, commands, exact=True):
        self.commands = commands
        self._exact = exact

    @property
    def exact(self):
        return self._exact

    def shell_commands(self):
        raw_commands = self.commands.replace("\n", ";")
        return raw_commands

    def __repr__(self):
        return "PlatformBrewDependency[commands=%s]" % self.commands
