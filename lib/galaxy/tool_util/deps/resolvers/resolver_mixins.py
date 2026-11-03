import os


class UsesToolDependencyDirMixin:
    def _init_base_path(self, dependency_manager, **kwds):
        self.base_path = os.path.abspath(kwds.get("base_path", dependency_manager.default_base_path))


class UsesInstalledRepositoriesMixin:
    def _get_installed_dependency(self, name, type, version=None, **kwds):
        installed_tool_dependencies = kwds.get("installed_tool_dependencies") or []
        for installed_tool_dependency in installed_tool_dependencies:
            if installed_tool_dependency.name == name and installed_tool_dependency.type == type:
                if not version or installed_tool_dependency.version == version:
                    return installed_tool_dependency
        return None
