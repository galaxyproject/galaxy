"""
API operations allowing clients to manage tool dependencies.
"""

import logging
from typing import Optional

from galaxy.managers.context import ProvidesAppContext
from galaxy.structured_app import StructuredApp
from galaxy.tool_util.deps import views
from galaxy.web import (
    expose_api,
    require_admin,
)
from . import BaseGalaxyAPIController

log = logging.getLogger(__name__)


class ToolDependenciesAPIController(BaseGalaxyAPIController):
    def __init__(self, app: StructuredApp):
        super().__init__(app)
        self._view = views.DependencyResolversView(app)

    @require_admin
    @expose_api
    def index(self, trans: ProvidesAppContext, **kwd):
        """
        GET /api/dependency_resolvers
        """
        return self._view.index()

    @require_admin
    @expose_api
    def show(self, trans: ProvidesAppContext, id: str):
        """
        GET /api/dependency_resolvers/<id>
        """
        return self._view.show(id)

    @require_admin
    @expose_api
    def update(self, trans):
        """
        PUT /api/dependency_resolvers

        Reload tool dependency resolution configuration.
        """
        return self._view.reload()

    @require_admin
    @expose_api
    def resolver_dependency(self, trans: ProvidesAppContext, id: str, **kwds):
        """
        GET /api/dependency_resolvers/{index}/dependency

        Resolve described requirement against specified dependency resolver.

        :type   index:    int
        :param  index:    index of the dependency resolver
        :type   kwds:     dict
        :param  kwds:     dictionary structure containing extra parameters
        :type   name:     str
        :param  name:     name of the requirement to find a dependency for (required)
        :type   version:  str
        :param  version:  version of the requirement to find a dependency for (required)
        :type   exact:    bool
        :param  exact:    require an exact match to specify requirement (do not discard
                          version information to resolve dependency).

        :rtype:     dict
        :returns:   a dictified description of the dependency, with attribute
                    ``dependency_type: None`` if no match was found.
        """
        return self._view.resolver_dependency(id, **kwds)

    @require_admin
    @expose_api
    def install_dependency(self, trans: ProvidesAppContext, id: Optional[str] = None, **kwds):
        """
        POST /api/dependency_resolvers/{index}/dependency
        POST /api/dependency_resolvers/dependency

        Install described requirement against specified dependency resolver.

        :type   index:    int
        :param  index:    index of the dependency resolver
        :type   kwds:     dict
        :param  kwds:     dictionary structure containing extra parameters
        :type   name:     str
        :param  name:     name of the requirement to find a dependency for (required)
        :type   version:  str
        :param  version:  version of the requirement to find a dependency for (required)
        :type   exact:    bool
        :param  exact:    require an exact match to specify requirement (do not discard
                          version information to resolve dependency).
        :type   tool_id:  str
        :param  tool_id:  tool_id to install requirements for

        :rtype:     dict
        :returns:   a dictified description of the dependency, with attribute
                    ``dependency_type: None`` if no match was found.
        """
        self._view.install_dependency(id, **kwds)
        return self._view.manager_dependency(**kwds)

    @require_admin
    @expose_api
    def manager_dependency(self, trans: ProvidesAppContext, **kwds):
        """
        GET /api/dependency_resolvers/dependency

        Resolve described requirement against all dependency resolvers, returning
        the match with highest priority.

        :type   index:    int
        :param  index:    index of the dependency resolver
        :type   kwds:     dict
        :param  kwds:     dictionary structure containing extra parameters
        :type   name:     str
        :param  name:     name of the requirement to find a dependency for (required)
        :type   version:  str
        :param  version:  version of the requirement to find a dependency for (required)
        :type   exact:    bool
        :param  exact:    require an exact match to specify requirement (do not discard
                          version information to resolve dependency).

        :rtype:     dict
        :returns:   a dictified description of the dependency, with type: None
                    if no match was found.
        """
        return self._view.manager_dependency(**kwds)

    @require_admin
    @expose_api
    def resolver_requirements(self, trans: ProvidesAppContext, id, **kwds):
        """
        GET /api/dependency_resolvers/{index}/requirements

        Find all "simple" requirements that could be resolved "exactly"
        by this dependency resolver. The dependency resolver must implement
        ListDependencyResolver.

        :type   index:    int
        :param  index:    index of the dependency resolver

        :rtype:     dict
        :returns:   a dictified description of the requirement that could
                    be resolved.
        """
        return self._view.resolver_requirements(id)

    @require_admin
    @expose_api
    def manager_requirements(self, trans: ProvidesAppContext, **kwds):
        """
        GET /api/dependency_resolvers/requirements

        Find all "simple" requirements that could be resolved "exactly"
        by all dependency resolvers that support this operation.

        :type   index:    int
        :param  index:    index of the dependency resolver

        :rtype:     dict
        :returns:   a dictified description of the requirement that could
                    be resolved (keyed on 'requirement') and the index of
                    the corresponding resolver (keyed on 'index').
        """
        return self._view.manager_requirements()

    @require_admin
    @expose_api
    def clean(self, trans: ProvidesAppContext, id=None, **kwds):
        """
        POST /api/dependency_resolvers/{index}/clean

        Cleans up intermediate files created by resolvers during the dependency
        installation.

        :type   index:    int
        :param  index:    index of the dependency resolver

        :rtype:     dict
        :returns:   a dictified description of the requirement that could
                    be resolved (keyed on 'requirement') and the index of
                    the corresponding resolver (keyed on 'index').
        """
        return self._view.clean(id, **kwds)

    @expose_api
    @require_admin
    def summarize_toolbox(self, trans: ProvidesAppContext, **kwds):
        """
        GET /api/dependency_resolvers/toolbox

        Summarize requirements across toolbox (for Tool Management grid). This is an experiemental
        API particularly tied to the GUI - expect breaking changes until this notice is removed.

        Container resolution via this API is especially experimental and the container resolution
        API should be used to summarize this information instead in most cases.

        :type   index:    int
        :param  index:    index of the dependency resolver
        :type   tool_ids: str
        :param  tool_ids: tool_id to install dependency for
        :type   resolver_type:  str
        :param  resolver_type:  restrict to uninstall to specified resolver type
        :type   include_containers: bool
        :param  include_containers: include container resolvers in resolution
        :type   container_type: str
        :param  container_type: restrict to uninstall to specified container type
        :type   index_by: str
        :param  index_by: By default consider only context of requirements, group tools by requirements.
                          Set this to 'tools' to summarize across all tools though. Tools may provide additional
                          context for container resolution for instance.

        :rtype:     list
        :returns:   dictified descriptions of the dependencies, with attribute
                    ``dependency_type: None`` if no match was found.
        """
        kwds["for_json"] = True
        index_by = kwds.get("index_by", "requirements")
        if index_by == "requirements":
            return self._view.summarize_requirements(**kwds)
        else:
            return self._view.summarize_tools(**kwds)

    @expose_api
    @require_admin
    def toolbox_install(self, trans: ProvidesAppContext, payload, index=None, **kwds):
        """
        POST /api/dependency_resolvers/{index}/toolbox/install
        POST /api/dependency_resolvers/toolbox/install

        Install described requirement against specified dependency resolver(s). This is an experiemental
        API particularly tied to the GUI - expect breaking changes until this notice is removed.

        :type   index:          int
        :param  index:          index of the dependency resolver
        :type   tool_ids:       str
        :param  tool_ids:       tool_id to install dependency for
        :type   resolver_type:  str
        :param  resolver_type:  restrict to uninstall to specified resolver type
        :type   include_containers: bool
        :param  include_containers: include container resolvers in resolution
        :type   container_type: str
        :param  container_type: restrict to uninstall to specified container type
        """
        tools_by_id = trans.app.toolbox.tools_by_id.copy()
        tool_ids = payload.get("tool_ids")
        requirements = {tools_by_id[tid].tool_requirements for tid in tool_ids}
        install_kwds = {}
        for source in [payload, kwds]:
            if "include_containers" in source:
                install_kwds["include_containers"] = source["container_type"]
            if "container_type" in kwds:
                install_kwds["container_type"] = source["container_type"]
            if "resolver_type" in source:
                install_kwds["resolver_type"] = source["resolver_type"]
        [self._view.install_dependencies(requirements=r, index=index, **install_kwds) for r in requirements]

    @expose_api
    @require_admin
    def toolbox_uninstall(self, trans: ProvidesAppContext, payload, index=None, **kwds):
        """
        POST /api/dependency_resolvers/{index}/toolbox/uninstall
        POST /api/dependency_resolvers/toolbox/uninstall

        Uninstall described requirement against specified dependency resolver(s). This is an experiemental
        API particularly tied to the GUI - expect breaking changes until this notice is removed.

        :type   index:          int
        :param  index:          index of the dependency resolver
        :type   tool_ids:       str
        :param  tool_ids:       tool_id to install dependency for
        :type   include_containers: bool
        :param  include_containers: include container resolvers in resolution
        :type   container_type: str
        :param  container_type: restrict to uninstall to specified container type
        :type   resolver_type:  str
        :param  resolver_type:  restrict to uninstall to specified resolver type
        """
        tools_by_id = self.app.toolbox.tools_by_id.copy()
        tool_ids = payload.get("tool_ids")
        requirements = {tools_by_id[tid].tool_requirements for tid in tool_ids}
        install_kwds = {}
        for source in [payload, kwds]:
            if "include_containers" in source:
                install_kwds["include_containers"] = source["container_type"]
            if "container_type" in kwds:
                install_kwds["container_type"] = source["container_type"]
            if "resolver_type" in source:
                install_kwds["resolver_type"] = source["resolver_type"]

        [self._view.uninstall_dependencies(index=index, requirements=r, **install_kwds) for r in requirements]

    @expose_api
    @require_admin
    def unused_dependency_paths(self, trans: ProvidesAppContext, **kwds):
        """
        GET /api/dependency_resolvers/unused_paths
        """
        return list(self._view.unused_dependency_paths)

    @expose_api
    @require_admin
    def delete_unused_dependency_paths(self, trans: ProvidesAppContext, payload, **kwds):
        """
        PUT /api/dependency_resolvers/unused_paths
        """
        paths = payload.get("paths")
        self._view.remove_unused_dependency_paths(paths)
