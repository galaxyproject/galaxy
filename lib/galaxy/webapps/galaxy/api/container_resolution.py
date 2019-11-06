"""
API operations allowing clients to manage container resolution.
"""
import logging

from galaxy.tool_util.deps import views
from galaxy.web import (
    expose_api,
    require_admin
)
from galaxy.webapps.base.controller import BaseAPIController

log = logging.getLogger(__name__)


class ContainerResolutionAPIController(BaseAPIController):

    def __init__(self, app):
        super(ContainerResolutionAPIController, self).__init__(app)
        self._view = views.ContainerResolutionView(app)

    @expose_api
    @require_admin
    def index(self, trans, **kwd):
        """
        GET /api/container_resolvers
        """
        return self._view.index()

    @expose_api
    @require_admin
    def show(self, trans, id):
        """
        GET /api/container_resolvers/<id>
        """
        return self._view.show(id)

    @expose_api
    @require_admin
    def resolve(self, trans, index=None, **kwds):
        """
        GET /api/container_resolvers/resolve
        GET /api/container_resolvers/{index}/resolve

        Resolve described requirement against specified container resolvers.

        :type   tool_id:            str
        :param  tool_id:            tool_id to resolve against containers
        :type   requirements_only:  boolean
        :param  requirements_only:  ignore tool containers, properties - just search based on tool requirements
                                    set to True to mimic default behavior of tool dependency API.
        :type   index:              int
        :param  index:              index of the container resolver, if unset resolvers searched in order
        :type   container_type:     str
        :param  container_type:     restrict resolution to specified container type (e.g. 'docker', 'singularity')
        :type   resolver_type:      str
        :param  resolver_type:      restrict resolution to specified resolver type (e.g. 'build_mulled', 'explicit')
        :type   install:            boolean
        :param  install:            allow installation of new containers (for build_mulled* containers) the way job resolution
                                    will operate, defaults to False
        :rtype:     dict
        :returns:   a dictified description of the container dependency, with attribute
                    ``dependency_type: None`` if no match was found.
        """
        return self._view.resolve(index=index, **kwds)

    @expose_api
    @require_admin
    def resolve_toolbox(self, trans, **kwds):
        """
        GET /api/container_resolvers/toolbox
        GET /api/container_resolvers/{index}/toolbox

        Apply resolve() to each tool in the toolbox and return the results as a list. See
        documentation for resolve() for a description of parameters that can be consumed and
        a description of the resulting items.

        :type   tool_ids:            str
        :param  tool_ids:            tool_ids to filter toolbox on

        :rtype:     list
        :returns:   list of items returned from resolve()
        """
        return self._view.resolve_toolbox(**kwds)

    @expose_api
    @require_admin
    def resolve_toolbox_with_install(self, trans, payload, **kwds):
        """
        POST /api/container_resolvers/toolbox/install
        POST /api/container_resolvers/{index}/toolbox/install

        Do the resolution of dependencies like resolve_toolbox(), but allow building
        and installing new containers. payload of POST body maybe contain same parameters
        as resolve_toolbox query parameters.

        :rtype:     list
        :returns:   list of items returned from resolve()
        """
        kwds.update(payload)
        kwds["install"] = True
        return self._view.resolve_toolbox(**kwds)

    @expose_api
    @require_admin
    def resolve_with_install(self, trans, payload, **kwds):
        """
        POST /api/container_resolvers/resolve/install
        POST /api/container_resolvers/{index}/resolve/install

        Do the resolution of dependencies like resolve(), but allow building
        and installing new containers during installation. payload of POST body maybe
        contain same parameters as resolve query parameters.

        :rtype:     dict
        :returns:   a dictified description of the container dependency, with attribute
                    ``dependency_type: None`` if no match was found.
        """
        kwds.update(payload)
        kwds["install"] = True
        return self._view.resolve(**kwds)
