"""The module defines the abstract interface for dealing tool dependency resolution plugins."""

import errno
import os.path
from abc import (
    ABCMeta,
    abstractmethod,
)
from typing import (
    Any,
    Dict,
    List,
)

import yaml

from galaxy.util import listify
from galaxy.util.dictifiable import Dictifiable
from ..requirements import (
    ToolRequirement,
    ToolRequirements,
)


class DependencyResolver(Dictifiable, metaclass=ABCMeta):
    """Abstract description of a technique for resolving container images for tool execution."""

    # Keys for dictification.
    dict_collection_visible_keys = [
        "resolver_type",
        "resolves_simple_dependencies",
        "can_uninstall_dependencies",
        "read_only",
    ]
    # A "simple" dependency is one that does not depend on the tool
    # resolving the dependency. Classic tool shed dependencies are non-simple
    # because the repository install context is used in dependency resolution
    # so the same requirement tags in different tools will have very different
    # resolution.
    disabled = False
    resolves_simple_dependencies = True
    config_options: Dict[str, Any] = {}
    read_only = True

    @abstractmethod
    def resolve(self, requirement: ToolRequirement, **kwds) -> "Dependency":
        """Given inputs describing dependency in the abstract yield a Dependency object.

        The Dependency object describes various attributes (script, bin,
        version) used to build scripts with the dependency availble. Here
        script is the env.sh file to source before running a job, if that is
        not found the bin directory will be appended to the path (if it is
        not ``None``). Finally, version is the resolved tool dependency
        version (which may differ from requested version for instance if the
        request version is 'default'.)
        """

    def install_dependency(self, name, version, type, **kwds):
        if self.read_only:
            return False
        else:
            return self._install_dependency(name, version, type, **kwds)

    def _install_dependency(self, name, version, type, **kwds):
        """Attempt to install this dependency if a recipe to do so
        has been registered in some way.
        """
        return False

    @property
    def can_uninstall_dependencies(self):
        return not self.read_only


class MultipleDependencyResolver:
    """Variant of DependencyResolver that can optionally resolve multiple dependencies together."""

    @abstractmethod
    def resolve_all(self, requirements: ToolRequirements, **kwds) -> List["Dependency"]:
        """
        Given multiple requirements yields a list of Dependency objects if and only if they may all be resolved together.

        Unsuccessfull attempts should return an empty list.

        :param requirements: list of tool requirements
        :param type: [ToolRequirement] or ToolRequirements

        :returns: list of resolved dependencies
        :rtype: [Dependency]
        """


class ListableDependencyResolver(metaclass=ABCMeta):
    """Mix this into a ``DependencyResolver`` and implement to indicate
    the dependency resolver can iterate over its dependencies and generate
    requirements.
    """

    @abstractmethod
    def list_dependencies(self):
        """List the "simple" requirements that may be resolved "exact"-ly
        by this dependency resolver.
        """

    def _to_requirement(self, name, version=None):
        return ToolRequirement(name=name, type="package", version=version)


class MappableDependencyResolver:
    """Mix this into a ``DependencyResolver`` to allow mapping files.

    Mapping files allow adapting generic requirements to specific local implementations.
    """

    def _setup_mapping(self, dependency_manager, **kwds):
        mapping_files = dependency_manager.get_resolver_option(self, "mapping_files", explicit_resolver_options=kwds)
        mappings = []
        if mapping_files:
            search_dirs = [os.getcwd()]
            if isinstance(dependency_manager.default_base_path, str):
                search_dirs.append(dependency_manager.default_base_path)

            def candidates(path):
                if os.path.isabs(path):
                    yield path
                else:
                    for search_dir in search_dirs:
                        yield os.path.join(search_dir, path)

            mapping_files = listify(mapping_files)
            for mapping_file in mapping_files:
                for full_path in candidates(mapping_file):
                    if os.path.exists(full_path):
                        mappings.extend(MappableDependencyResolver._mapping_file_to_list(full_path))
                        break
        self._mappings = mappings

    @staticmethod
    def _mapping_file_to_list(mapping_file):
        raw_mapping = []
        try:
            with open(mapping_file) as f:
                raw_mapping = yaml.safe_load(f)
        except OSError as exc:
            if exc.errno != errno.ENOENT:
                raise
        return list(map(RequirementMapping.from_dict, raw_mapping))

    def _expand_mappings(self, requirement):
        for mapping in self._mappings:
            if mapping.matches_requirement(requirement):
                requirement = mapping.apply(requirement)
                break

        return requirement


FROM_UNVERSIONED = object()


class RequirementMapping:
    def __init__(self, from_name, from_version, to_name, to_version):
        self.from_name = from_name
        self.from_version = from_version
        self.to_name = to_name
        self.to_version = to_version

    def matches_requirement(self, requirement):
        """Check if supplied ToolRequirement matches this mapping description.

        For it to match - the names must match. Additionally if the
        requirement is created with a version or with unversioned being set to
        True additional checks are needed. If a version is specified, it must
        match the supplied version exactly. If ``unversioned`` is True, then
        the supplied requirement must be unversioned (i.e. its version must be
        set to ``None``).
        """

        if requirement.name != self.from_name:
            return False
        elif self.from_version is None:
            return True
        elif self.from_version is FROM_UNVERSIONED:
            return requirement.version is None
        else:
            return requirement.version == self.from_version

    def apply(self, requirement):
        requirement = requirement.copy()
        requirement.name = self.to_name
        if self.to_version is not None:
            requirement.version = self.to_version
        return requirement

    @staticmethod
    def from_dict(raw_mapping):
        from_raw = raw_mapping.get("from")
        if isinstance(from_raw, dict):
            from_name = from_raw.get("name")
            raw_version = from_raw.get("version", None)
            unversioned = from_raw.get("unversioned", False)
            if unversioned and raw_version:
                raise Exception("Cannot define both version and set unversioned to True.")

            if unversioned:
                from_version = FROM_UNVERSIONED
            else:
                from_version = str(raw_version) if raw_version is not None else raw_version
        else:
            from_name = from_raw
            from_version = None

        to_raw = raw_mapping.get("to")
        if isinstance(to_raw, dict):
            to_name = to_raw.get("name", from_name)
            to_version = str(to_raw.get("version"))
        else:
            to_name = to_raw
            to_version = None

        return RequirementMapping(from_name, from_version, to_name, to_version)


class SpecificationAwareDependencyResolver(metaclass=ABCMeta):
    """Mix this into a :class:`DependencyResolver` to implement URI specification matching.

    Allows adapting generic requirements to more specific URIs - to tailor name
    or version to specified resolution system.
    """

    @abstractmethod
    def _expand_specs(self, requirement):
        """Find closest matching specification for discovered resolver and return new concrete requirement."""


class SpecificationPatternDependencyResolver(SpecificationAwareDependencyResolver):
    """Implement the :class:`SpecificationAwareDependencyResolver` with a regex pattern."""

    @property
    @abstractmethod
    def _specification_pattern(self):
        """Pattern of URI to match against."""

    def _find_specification(self, specs):
        pattern = self._specification_pattern
        for spec in specs:
            if pattern.match(spec.uri):
                return spec
        return None

    def _expand_specs(self, requirement):
        name = requirement.name
        version = requirement.version
        specs = requirement.specs

        spec = self._find_specification(specs)
        if spec is not None:
            name = spec.short_name
            version = spec.version or version

            requirement = requirement.copy()
            requirement.name = name
            requirement.version = version

        return requirement


class Dependency(Dictifiable, metaclass=ABCMeta):
    dict_collection_visible_keys = ["dependency_type", "exact", "name", "version", "cacheable"]
    cacheable = False

    @abstractmethod
    def shell_commands(self):
        """
        Return shell commands to enable this dependency.
        """

    @property
    @abstractmethod
    def exact(self):
        """Return true if version information wasn't discarded to resolve
        the dependency.
        """

    @property
    def resolver_msg(self):
        """
        Return a message describing this dependency
        """
        return f"Using dependency {self.name} version {self.version} of type {self.dependency_type}"


class ContainerDependency(Dependency):
    dict_collection_visible_keys = Dependency.dict_collection_visible_keys + [
        "environment_path",
        "container_description",
        "container_resolver",
    ]

    def __init__(self, container_description, name=None, version=None, container_resolver=None):
        self.container_description = container_description
        self.dependency_type = container_description.type
        self._name = name
        self._version = version
        self.environment_path = container_description.identifier
        self.container_resolver = container_resolver

    @property
    def name(self):
        return self._name

    @property
    def version(self):
        return self._version

    @property
    def exact(self):
        return True

    @property
    def shell_commands(self):
        return None


class NullDependency(Dependency):
    dependency_type = None
    exact = True

    def __init__(self, version=None, name=None):
        self.version = version
        self.name = name

    @property
    def resolver_msg(self):
        """
        Return a message describing this dependency
        """
        return f"Dependency {self.name} not found."

    def shell_commands(self):
        return None


class DependencyException(Exception):
    pass
