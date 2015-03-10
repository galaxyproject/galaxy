import os
from ..brew_exts import DEFAULT_HOMEBREW_ROOT, recipe_cellar_path, build_env_statements
from ..resolvers import INDETERMINATE_DEPENDENCY, Dependency


class UsesHomebrewMixin:

    def _init_homebrew(self, **kwds):
        cellar_root = kwds.get('cellar', None)
        if cellar_root is None:
            cellar_root = os.path.join(DEFAULT_HOMEBREW_ROOT, "Cellar")

        self.cellar_root = cellar_root

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


class UsesToolDependencyDirMixin:

    def _init_base_path(self, dependency_manager, **kwds):
        self.base_path = os.path.abspath( kwds.get('base_path', dependency_manager.default_base_path) )


class UsesInstalledRepositoriesMixin:

    def _get_installed_dependency( self, name, type, version=None, **kwds ):
        installed_tool_dependencies = kwds.get("installed_tool_dependencies", [])
        for installed_tool_dependency in (installed_tool_dependencies or []):
            name_and_type_equal = installed_tool_dependency.name == name and installed_tool_dependency.type == type
            if version:
                if name_and_type_equal and installed_tool_dependency.version == version:
                    return installed_tool_dependency
            else:
                if name_and_type_equal:
                    return installed_tool_dependency
        return None


class HomebrewDependency(Dependency):

    def __init__(self, commands):
        self.commands = commands

    def shell_commands(self, requirement):
        raw_commands = self.commands.replace("\n", ";")
        return raw_commands

    def __repr__(self):
        return "PlatformBrewDependency[commands=%s]" % self.commands
