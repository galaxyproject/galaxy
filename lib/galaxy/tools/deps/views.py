from galaxy.exceptions import (
    NotImplemented,
    RequestParameterMissingException
)


class DependencyResolversView(object):
    """ Provide a RESTfulish/JSONy interface to a galaxy.tools.deps.DependencyResolver
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
            raise NotImplemented()
        for requirement in resolver.list_dependencies():
            requirements.append(requirement.to_dict())
        return requirements

    def manager_dependency(self, **kwds):
        return self._dependency(**kwds)

    def resolver_dependency(self, index, **kwds):
        return self._dependency(**kwds)

    def show_dependencies(self, tool_requirements_d, installed_tool_dependencies=None):
        """
        Resolves dependencies to build a requirements status in the admin panel/API
        """
        kwds = {'install': False,
                'return_null': True,
                'installed_tool_dependencies': installed_tool_dependencies}
        dependencies_per_tool = {tool: self._dependency_manager.requirements_to_dependencies(requirements, **kwds) for tool, requirements in tool_requirements_d.items()}
        return dependencies_per_tool

    def install_dependencies(self, requirements):
        return self._dependency_manager._requirements_to_dependencies_dict(requirements, **{'install': True})

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
            raise NotImplemented()

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
            raise RequestParameterMissingException("Missing 'name' parameter required for resolution.")
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
        List index for all active resolvers that have the 'install_dependency' attribute
        """
        return [index for index, resolver in enumerate(self._dependency_resolvers) if hasattr(resolver, "install_dependency") and not resolver.disabled ]

    def get_requirements_status(self, tool_requirements_d, installed_tool_dependencies=None):
        dependencies = self.show_dependencies(tool_requirements_d, installed_tool_dependencies)
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
                raise NotImplemented()
            else:
                resolver.clean()
                return "OK"
        else:
            [resolver.clean(**kwds) for resolver in self._dependency_resolvers if hasattr(resolver, 'clean')]
            return "OK"
