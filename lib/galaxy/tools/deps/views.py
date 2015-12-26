from galaxy.exceptions import (
    RequestParameterMissingException,
    NotImplemented
)


class DependencyResolversView(object):
    """ Provide a RESTfulish/JSONy interface to a galaxy.tools.deps.DependencyResolver
    object. This can be adapted by the Galaxy web framework or other web apps.
    """

    def __init__(self, app):
        self._app = app

    def index(self):
        return map(lambda r: r.to_dict(), self._dependency_resolvers)

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

    def _dependency(self, index=None, **kwds):
        if index is not None:
            index = int(index)

        name = kwds.get("name", None)
        if name is None:
            raise RequestParameterMissingException("Missing 'name' parameter required for resolution.")
        version = kwds.get("version", None)
        type = kwds.get("type", "package")
        resolve_kwds = dict(
            job_directory="/path/to/example/job_directory",
            index=index,
        )
        dependency = self._dependency_manager.find_dep(
            name, version=version, type=type, **resolve_kwds
        )
        return dependency.to_dict()

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
