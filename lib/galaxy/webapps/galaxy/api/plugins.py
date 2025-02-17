"""
Plugins resource control over the API.
"""

import logging

from galaxy import exceptions
from galaxy.managers import (
    hdas,
    histories,
)
from galaxy.util import asbool
from galaxy.web import (
    expose_api,
    expose_api_anonymous_and_sessionless,
)
from . import (
    BaseGalaxyAPIController,
    depends,
)

log = logging.getLogger(__name__)


class PluginsController(BaseGalaxyAPIController):
    """
    RESTful controller for interactions with plugins.
    """

    hda_manager: hdas.HDAManager = depends(hdas.HDAManager)
    history_manager: histories.HistoryManager = depends(histories.HistoryManager)

    @expose_api_anonymous_and_sessionless
    def index(self, trans, **kwargs):
        """
        GET /api/plugins:
        """
        registry = self._get_registry()
        embeddable = asbool(kwargs.get("embeddable"))
        target_object = None
        if (dataset_id := kwargs.get("dataset_id")) is not None:
            target_object = self.hda_manager.get_accessible(self.decode_id(dataset_id), trans.user)
        return registry.get_visualizations(trans, target_object=target_object, embeddable=embeddable)

    @expose_api
    def show(self, trans, id, **kwargs):
        """
        GET /api/plugins/{id}:
        """
        registry = self._get_registry()
        if (history_id := kwargs.get("history_id")) is not None:
            history = self.history_manager.get_owned(
                trans.security.decode_id(history_id), trans.user, current_history=trans.history
            )
            result = {"hdas": []}
            for hda in history.contents_iter(types=["dataset"], deleted=False, visible=True):
                if registry.get_visualization(trans, id, hda):
                    result["hdas"].append({"id": trans.security.encode_id(hda.id), "name": hda.name})
        else:
            result = registry.get_plugin(id).to_dict()
        return result

    def _get_registry(self):
        if not self.app.visualizations_registry:
            raise exceptions.MessageException("The visualization registry has not been configured.")
        return self.app.visualizations_registry
