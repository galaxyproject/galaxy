"""
Plugins resource control over the API.
"""
import logging

from galaxy import (
    exceptions,
    util,
    web
)
from galaxy.model.item_attrs import UsesAnnotations
from galaxy.web import _future_expose_api as expose_api
from galaxy.web.base.controller import (
    BaseAPIController,
    SharableMixin,
    UsesVisualizationMixin
)

log = logging.getLogger(__name__)


class PluginsController(BaseAPIController):
    """
    RESTful controller for interactions with plugins.
    """

    @expose_api
    def index(self, trans, **kwargs):
        """
        GET /api/plugins:
        """
        if not trans.app.visualizations_registry:
            raise exceptions.MessageException('No visualization registry (possibly disabled in galaxy.ini)')
        return trans.app.visualizations_registry.get_plugins()
