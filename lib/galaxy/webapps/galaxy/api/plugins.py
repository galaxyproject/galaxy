"""
Plugins resource control over the API.
"""
import logging

from galaxy import exceptions
from galaxy.managers import hdas, histories
from galaxy.web import _future_expose_api as expose_api
from galaxy.web.base.controller import BaseAPIController

log = logging.getLogger(__name__)


class PluginsController(BaseAPIController):
    """
    RESTful controller for interactions with plugins.
    """

    def __init__(self, app):
        super(PluginsController, self).__init__(app)
        self.hda_manager = hdas.HDAManager(app)
        self.history_manager = histories.HistoryManager(app)

    @expose_api
    def index(self, trans, **kwargs):
        """
        GET /api/plugins:
        """
        registry = self._get_registry(trans)
        dataset_id = kwargs.get("dataset_id")
        if dataset_id is not None:
            hda = self.hda_manager.get_accessible(self.decode_id(dataset_id), trans.user)
            return registry.get_visualizations(trans, hda)
        else:
            return registry.get_plugins()

    @expose_api
    def show(self, trans, id, **kwargs):
        """
        GET /api/plugins/{id}:
        """
        registry = self._get_registry(trans)
        result = {}
        history_id = kwargs.get("history_id")
        if history_id is not None:
            history = self.history_manager.get_owned(trans.security.decode_id(history_id), trans.user, current_history=trans.history)
            result["hdas"] = []
            for hda in history.datasets:
                if registry.get_visualization(trans, id, hda):
                    result["hdas"].append({
                        "id": trans.security.encode_id(hda.id),
                        "name": hda.name
                    })
        return result

    def _get_registry(self, trans):
        if not trans.app.visualizations_registry:
            raise exceptions.MessageException("The visualization registry has not been configured.")
        return trans.app.visualizations_registry
