"""
This dependency resolver resolves tool shed dependencies (those defined
tool_dependencies.xml) installed using Platform Homebrew and converted
via shed2tap (e.g. https://github.com/jmchilton/homebrew-toolshed).
"""
import logging
import os
from xml.etree import ElementTree as ET

from .resolver_mixins import (
    UsesHomebrewMixin,
    UsesToolDependencyDirMixin,
    UsesInstalledRepositoriesMixin,
)
from ..resolvers import DependencyResolver, INDETERMINATE_DEPENDENCY

log = logging.getLogger(__name__)


class HomebrewToolShedDependencyResolver(
    DependencyResolver,
    UsesHomebrewMixin,
    UsesToolDependencyDirMixin,
    UsesInstalledRepositoriesMixin,
):
    resolver_type = "tool_shed_tap"

    def __init__(self, dependency_manager, **kwds):
        self._init_homebrew(**kwds)
        self._init_base_path(dependency_manager, **kwds)

    def resolve(self, name, version, type, **kwds):
        if type != "package":
            return INDETERMINATE_DEPENDENCY

        if version is None:
            return INDETERMINATE_DEPENDENCY

        return self._find_tool_dependencies(name, version, type, **kwds)

    def _find_tool_dependencies(self, name, version, type, **kwds):
        installed_tool_dependency = self._get_installed_dependency(name, type, version=version, **kwds)
        if installed_tool_dependency:
            return self._resolve_from_installed_tool_dependency(name, version, installed_tool_dependency)

        if "tool_dir" in kwds:
            tool_directory = os.path.abspath(kwds["tool_dir"])
            tool_depenedencies_path = os.path.join(tool_directory, "tool_dependencies.xml")
            if os.path.exists(tool_depenedencies_path):
                return self._resolve_from_tool_dependencies_path(name, version, tool_depenedencies_path)

        return INDETERMINATE_DEPENDENCY

    def _resolve_from_installed_tool_dependency(self, name, version, installed_tool_dependency):
        tool_shed_repository = installed_tool_dependency.tool_shed_repository
        recipe_name = build_recipe_name(
            package_name=name,
            package_version=version,
            repository_owner=tool_shed_repository.owner,
            repository_name=tool_shed_repository.name,
        )
        return self._find_dep_default(recipe_name, None)

    def _resolve_from_tool_dependencies_path(self, name, version, tool_dependencies_path):
        try:
            raw_dependencies = RawDependencies(tool_dependencies_path)
        except Exception:
            log.debug("Failed to parse dependencies in file %s" % tool_dependencies_path)
            return INDETERMINATE_DEPENDENCY

        raw_dependency = raw_dependencies.find(name, version)
        if not raw_dependency:
            return INDETERMINATE_DEPENDENCY

        recipe_name = build_recipe_name(
            package_name=name,
            package_version=version,
            repository_owner=raw_dependency.repository_owner,
            repository_name=raw_dependency.repository_name
        )
        dep = self._find_dep_default(recipe_name, None)
        return dep


class RawDependencies(object):

    def __init__(self, dependencies_file):
        self.root = ET.parse(dependencies_file).getroot()
        dependencies = []
        package_els = self.root.findall("package") or []
        for package_el in package_els:
            repository_el = package_el.find("repository")
            if repository_el is None:
                continue
            dependency = RawDependency(self, package_el, repository_el)
            dependencies.append(dependency)
        self.dependencies = dependencies

    def find(self, package_name, package_version):
        target_dependency = None

        for dependency in self.dependencies:
            if dependency.package_name == package_name and dependency.package_version == package_version:
                target_dependency = dependency
                break
        return target_dependency


class RawDependency(object):

    def __init__(self, dependencies, package_el, repository_el):
        self.dependencies = dependencies
        self.package_el = package_el
        self.repository_el = repository_el

    def __repr__(self):
        temp = "Dependency[package_name=%s,version=%s,dependent_package=%s]"
        return temp % (
            self.package_el.attrib["name"],
            self.package_el.attrib["version"],
            self.repository_el.attrib["name"]
        )

    @property
    def repository_owner(self):
        return self.repository_el.attrib["owner"]

    @property
    def repository_name(self):
        return self.repository_el.attrib["name"]

    @property
    def package_name(self):
        return self.package_el.attrib["name"]

    @property
    def package_version(self):
        return self.package_el.attrib["version"]


def build_recipe_name(package_name, package_version, repository_owner, repository_name):
    # TODO: Consider baking package_name and package_version into name? (would be more "correct")
    owner = repository_owner.replace("-", "")
    name = repository_name
    name = name.replace("_", "").replace("-", "")
    base = "%s_%s" % (owner, name)
    return base


__all__ = ['HomebrewToolShedDependencyResolver']
