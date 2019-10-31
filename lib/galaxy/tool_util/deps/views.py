from galaxy import exceptions
from galaxy.util import asbool, listify
from .container_resolvers import ResolutionCache
from .dependencies import ToolInfo
from .resolvers import (
    ContainerDependency,
    NullDependency,
)


class DependencyResolversView(object):
    """ Provide a RESTfulish/JSONy interface to a galaxy.tool_util.deps.DependencyResolver
    object. This can be adapted by the Galaxy web framework or other web apps.
    """

    def __init__(self, app):
        self._app = app

    def index(self):
        return [r.to_dict() for r in self._dependency_resolvers]

    def show(self, index):
        return self._dependency_resolver(index).to_dict()

    def reload(self):
        self.toolbox.reload_dependency_manager()

    def manager_requirements(self):
        requirements = []
        for index, resolver in enumerate(self._dependency_resolvers):
            if not hasattr(resolver, "list_dependencies"):
                continue
            for requirement in resolver.list_dependencies():
                requirements.append({"index": index, "requirement": requirement.to_dict()})
        return requirements

    def resolver_requirements(self, index):
        requirements = []
        resolver = self._dependency_resolver(index)
        if not hasattr(resolver, "list_dependencies"):
            raise exceptions.NotImplemented()
        for requirement in resolver.list_dependencies():
            requirements.append(requirement.to_dict())
        return requirements

    def manager_dependency(self, **kwds):
        return self._dependency(**kwds)

    def resolver_dependency(self, index, **kwds):
        return self._dependency(**kwds)

    def show_dependencies(self, tool_requirements_d, installed_tool_dependencies=None, **kwd):
        """
        Resolves dependencies to build a requirements status in the admin panel/API
        """
        to_deps_kwds = {
            'install': False,
            'return_null': True,
            'installed_tool_dependencies': installed_tool_dependencies
        }
        to_deps_kwds.update(kwd)
        dependencies_per_tool = {tool: self._dependency_manager.requirements_to_dependencies(requirements,
                                                                                             **to_deps_kwds)
                                 for tool, requirements in tool_requirements_d.items()}
        return dependencies_per_tool

    def uninstall_dependencies(self, index=None, resolver_type=None, container_type=None, **payload):
        """Attempt to uninstall requirements. Returns 0 if successfull, else None."""
        requirements = payload.get('requirements')
        if not requirements:
            return None
        if index:
            resolver = self._dependency_resolvers[index]
            if resolver.can_uninstall_dependencies:
                return resolver.uninstall(requirements)
        elif resolver_type:
            for resolver in self._dependency_resolvers:
                if resolver.resolver_type == resolver_type and resolver.can_uninstall_dependencies:
                    return resolver.uninstall(requirements)
        elif container_type:
            for resolver in self._dependency_resolvers:
                if getattr(resolver, "container_type", None) == container_type and resolver.can_uninstall_dependencies:
                    return resolver.uninstall(requirements)
        else:
            for index in self.uninstallable_resolvers:
                return_code = self._dependency_resolvers[index].uninstall(requirements)
                if return_code == 0:
                    return return_code
        return None

    @property
    def unused_dependency_paths(self):
        """List dependencies that are not currently installed."""
        unused_dependencies = []
        toolbox_requirements_status = self.toolbox_requirements_status
        for resolver in self._dependency_resolvers:
            if hasattr(resolver, 'unused_dependency_paths'):
                unused_dependencies.extend(resolver.unused_dependency_paths(toolbox_requirements_status))
        return set(unused_dependencies)

    def remove_unused_dependency_paths(self, envs):
        """
        Remove dependencies that are not currently used.

        Returns a list of all environments that have been successfully removed.
        """
        envs_to_remove = set(envs)
        toolbox_requirements_status = self.toolbox_requirements_status
        removed_environments = set()
        for resolver in self._dependency_resolvers:
            if hasattr(resolver, 'unused_dependency_paths') and hasattr(resolver, 'uninstall_environments'):
                unused_dependencies = resolver.unused_dependency_paths(toolbox_requirements_status)
                can_remove = envs_to_remove & set(unused_dependencies)
                exit_code = resolver.uninstall_environments(can_remove)
                if exit_code == 0:
                    removed_environments = removed_environments.union(can_remove)
                    envs_to_remove = envs_to_remove.difference(can_remove)
        return list(removed_environments)

    def install_dependencies(self, requirements, **kwds):
        kwds['install'] = True
        return self._dependency_manager._requirements_to_dependencies_dict(requirements, **kwds)

    def install_dependency(self, index=None, **payload):
        """
        Installs dependency using highest priority resolver that supports dependency installation
        (Currently only the conda resolver supports this). If index is given, attempt
        installation directly using the corresponding resolver.
        Returns True on success, False on failure.
        payload is dictionary that must container name, version and type,
        e.g. {'name': 'numpy', version='1.9.1', type='package'}
        """
        if index:
            return self._install_dependency(index, **payload)
        else:
            for index in self.installable_resolvers:
                success = self._install_dependency(index, **payload)
                if success:
                    return success
            return False

    def _install_dependency(self, index, **payload):
        """
        Resolver install dependency should return True when installation succeeds,
        False if not successful
        """
        resolver = self._dependency_resolver(index)
        if not hasattr(resolver, "install_dependency"):
            raise exceptions.NotImplemented()

        name, version, type, extra_kwds = self._parse_dependency_info(payload)
        return resolver.install_dependency(
            name=name,
            version=version,
            type=type,
            **extra_kwds
        )

    def _dependency(self, index=None, **kwds):
        if index is not None:
            index = int(index)

        name, version, type, extra_kwds = self._parse_dependency_info(kwds)
        resolve_kwds = dict(
            job_directory=None,
            index=index,
            **extra_kwds
        )
        dependency = self._dependency_manager.find_dep(
            name, version=version, type=type, **resolve_kwds
        )
        return dependency.to_dict()

    def _parse_dependency_info(self, kwds):
        extra_kwds = kwds.copy()
        name = extra_kwds.pop("name", None)
        if name is None:
            raise exceptions.RequestParameterMissingException("Missing 'name' parameter required for resolution.")
        version = extra_kwds.pop("version", None)
        type = extra_kwds.pop("type", "package")
        return name, version, type, extra_kwds

    def _dependency_resolver(self, index):
        index = int(index)
        return self._dependency_resolvers[index]

    @property
    def _dependency_manager(self):
        return self._app.toolbox.dependency_manager

    @property
    def _dependency_resolvers(self):
        dependency_manager = self._dependency_manager
        dependency_resolvers = dependency_manager.dependency_resolvers
        return dependency_resolvers

    @property
    def installable_resolvers(self):
        """
        List index for all active resolvers that have the 'install_dependency' attribute.
        """
        return [index for index, resolver in enumerate(self._dependency_resolvers) if hasattr(resolver, "install_dependency") and not resolver.disabled]

    @property
    def uninstallable_resolvers(self):
        """
        List index for all active resolvers that can uninstall dependencies that have been installed through this resolver.
        """
        return [index for index, resolver in enumerate(self._dependency_resolvers) if resolver.can_uninstall_dependencies and not resolver.disabled]

    @property
    def tool_ids_by_requirements(self):
        """Dictionary with requirements as keys, and tool_ids as values."""
        tool_ids_by_requirements = {}
        if not self._app.toolbox.tools_by_id:
            return {}
        for tid, tool in self._app.toolbox.tools_by_id.items():
            if tool.tool_requirements not in tool_ids_by_requirements:
                tool_ids_by_requirements[tool.tool_requirements] = [tid]
            else:
                tool_ids_by_requirements[tool.tool_requirements].append(tid)
        return tool_ids_by_requirements

    @property
    def toolbox_requirements_status(self):
        return self.summarize_requirements()

    def summarize_requirements(self, **kwds):
        summary_kwds = {}
        if 'index' in kwds:
            summary_kwds['index'] = int(kwds['index'])
        if 'container_type' in kwds:
            summary_kwds['container_type'] = kwds['container_type']
        if 'resolver_type' in kwds:
            summary_kwds['resolver_type'] = kwds['resolver_type']
        if 'search' in kwds:
            summary_kwds['search'] = asbool(kwds['search'])
        if 'install' in kwds:
            summary_kwds['install'] = asbool(kwds['install'])

        statuses = {r: self.get_requirements_status(tool_requirements_d={tids[0]: r},
                                                installed_tool_dependencies=self._app.toolbox.tools_by_id[tids[0]].installed_tool_dependencies, **summary_kwds)
                for r, tids in self.tool_ids_by_requirements.items()}
        if kwds.get("for_json", False):
            # All public attributes of this class should be returning JSON - this is meant to mimic a restful API.
            rval = []
            for requirements, status in statuses.items():
                item = {}
                item["requirements"] = requirements.to_dict()
                item["status"] = status
                item["tool_ids"] = self.tool_ids_by_requirements[requirements]
                rval.append(item)
            statuses = rval
        return statuses

    def summarize_tools(self, **kwds):
        summary_kwds = {}
        if 'index' in kwds:
            summary_kwds['index'] = int(kwds['index'])
        if 'container_type' in kwds:
            summary_kwds['container_type'] = kwds['container_type']
        if 'resolver_type' in kwds:
            summary_kwds['resolver_type'] = kwds['resolver_type']
        if 'search' in kwds:
            summary_kwds['search'] = asbool(kwds['search'])
        if 'install' in kwds:
            summary_kwds['install'] = asbool(kwds['install'])

        rval = []
        for tid, tool in self._app.toolbox.tools_by_id.items():
            requirements = tool.tool_requirements
            status = self.get_requirements_status(tool_requirements_d={tid: requirements},
                                                  installed_tool_dependencies=tool.installed_tool_dependencies,
                                                  tool_instance=tool, **summary_kwds)
            item = {}
            item["requirements"] = requirements.to_dict()
            item["status"] = status
            item["tool_ids"] = [tid]
            rval.append(item)
        return rval

    def get_requirements_status(self, tool_requirements_d, installed_tool_dependencies=None, **kwd):
        dependencies = self.show_dependencies(tool_requirements_d, installed_tool_dependencies, **kwd)
        # dependencies is a dict keyed on tool_ids, value is a ToolRequirements object for that tool.
        # We use the union of resolvable ToolRequirements to get resolved dependencies without duplicates.
        requirements = [r.resolvable for r in tool_requirements_d.values()]
        flat_tool_requirements = set().union(*requirements)
        flat_dependencies = []
        for requirements_odict in dependencies.values():
            for requirement in requirements_odict:
                if requirement in flat_tool_requirements:
                    flat_dependencies.append(requirements_odict[requirement])
                    flat_tool_requirements.remove(requirement)
        return [d.to_dict() for d in flat_dependencies]

    def clean(self, index=None, **kwds):
        if index:
            resolver = self._dependency_resolver(index)
            if not hasattr(resolver, "clean"):
                raise exceptions.NotImplemented()
            else:
                resolver.clean()
                return "OK"
        else:
            [resolver.clean(**kwds) for resolver in self._dependency_resolvers if hasattr(resolver, 'clean')]
            return "OK"


class ContainerResolutionView(object):
    """
    """

    def __init__(self, app):
        self._app = app

    def index(self):
        return [r.to_dict() for r in self._container_resolvers]

    def show(self, index):
        return self._container_resolver(index).to_dict()

    def resolve(self, **kwds):
        find_best_kwds = {
            'install': False,
            'enabled_container_types': ['docker', 'singularity'],
            'resolution_cache': kwds.get("resolution_cache"),
        }

        if 'index' in kwds:
            find_best_kwds['index'] = int(kwds['index'])
        if 'container_type' in kwds:
            find_best_kwds['enabled_container_types'] = [kwds['container_type']]
        if 'resolver_type' in kwds:
            find_best_kwds['resolver_type'] = kwds['resolver_type']
        if 'install' in kwds:
            find_best_kwds['install'] = asbool(kwds['install'])

        tool_info_kwds = {}
        tool_id = kwds["tool_id"]
        tool = self._app.toolbox.tools_by_id[tool_id]

        requirements = tool.tool_requirements
        tool_info_kwds = dict(requirements=requirements)
        requirements_only = asbool(kwds.get("requirements_only", False))
        # If requirements_only, simply use the tool to load a requirement set from,
        # mimics the default behavior of searching for containers through the dependency resolution
        # component. Not useful for tool execution but perhaps when summarizing mulled containers for requirements.
        if not requirements_only:
            tool_info_kwds['container_descriptions'] = tool.containers
            tool_info_kwds['requires_galaxy_python_environment'] = tool.requires_galaxy_python_environment
            tool_info_kwds['tool_id'] = tool.id
            tool_info_kwds['tool_version'] = tool.version

        find_best_kwds["tool_info"] = ToolInfo(**tool_info_kwds)

        # Consider implementing 'search' to match dependency resolution API.
        resolved_container_description = self._app.container_finder.resolve(
            **find_best_kwds
        )
        if resolved_container_description:
            status = ContainerDependency(resolved_container_description.container_description, container_resolver=resolved_container_description.container_resolver).to_dict()
        else:
            status = NullDependency().to_dict()
        return {
            "tool_id": kwds["tool_id"],
            "status": status,
            "requirements": requirements.to_dict()
        }

    def resolve_toolbox(self, **kwds):
        rval = []
        resolve_kwds = kwds.copy()
        tool_ids = resolve_kwds.pop("tool_ids", None)
        resolve_kwds["resolution_cache"] = ResolutionCache()
        if tool_ids is not None:
            tool_ids = listify(tool_ids)
        for tool_id, tool in self._app.toolbox.tools_by_id.items():
            if tool_ids is not None and tool_id in tool_ids:
                continue

            if tool.tool_action.produces_real_jobs:
                rval.append(self.resolve(tool_id=tool_id, **resolve_kwds))
        return rval

    @property
    def _container_resolvers(self):
        return self._app.container_finder.container_resolvers

    def _container_resolver(self, index):
        index = int(index)
        return self._container_resolvers[index]
