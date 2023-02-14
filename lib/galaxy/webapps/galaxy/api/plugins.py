"""
Plugins resource control over the API.
"""
import logging
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from fastapi import (
    Path,
    Query,
)
from pydantic import (
    BaseModel,
    Field,
)

from galaxy import exceptions
from galaxy.managers import (
    hdas,
    histories,
)
from galaxy.managers.context import (
    ProvidesHistoryContext,
    ProvidesUserContext,
)
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.web import (
    expose_api_anonymous_and_sessionless,
)
from . import (
    depends,
    DependsOnTrans,
    Router,
)

log = logging.getLogger(__name__)

router = Router(tags=["plugins"])


class VisualizationPlugin(BaseModel):
    name: str = Field(title="Name", description="Name of the plugin")
    html: str = Field(title="HTML", description="HTML of the plugin")
    description: Optional[str] = Field(title="Description", description="Description of the plugin")
    logo: Optional[str] = Field(title="Logo", description="Logo of the plugin")
    title: Optional[str] = Field(title="Title", description="Title of the plugin")
    target: str = Field(title="Target", description="Target frame of the plugin")
    # TODO: formalize these Any types, document remainder.
    embeddable: bool
    entry_point: Dict[str, Any]
    settings: Optional[List[Dict[str, Any]]]
    groups: Optional[List[Dict]]
    specs: Optional[Dict[str, Any]]
    href: str


@router.cbv
class FastAPIPlugins:
    hda_manager: hdas.HDAManager = depends(hdas.HDAManager)
    history_manager: histories.HistoryManager = depends(histories.HistoryManager)

    @expose_api_anonymous_and_sessionless
    @router.get(
        "/api/plugins",
        summary="Get a list of all available plugins",
        response_description="List of plugins",
    )
    def index(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        dataset_id: Optional[DecodedDatabaseIdField] = Query(
            default=None,
            description="The encoded database identifier of the Dataset to get appropriate plugins for.",
        ),
        embeddable: Optional[bool] = Query(
            default=False,
            description="Whether to return only embeddable plugins.",
        ),
    ) -> List[VisualizationPlugin]:
        registry = self._get_registry()
        if dataset_id is not None:
            hda = self.hda_manager.get_accessible(dataset_id, trans.user)
            return registry.get_visualizations(trans, hda)
        else:
            plugins = registry.get_plugins(embeddable=embeddable)
            return plugins

    @router.get(
        "/api/plugins/{id}",
        summary="Get a plugin by id",
        response_description="Plugin",
    )
    def show(
        self,
        trans: ProvidesHistoryContext = DependsOnTrans,
        id: str = Path(title="Plugin ID", description="The plugin ID"),
        history_id: Optional[DecodedDatabaseIdField] = Query(
            default=None,
            description="The encoded database identifier of the History.",
        ),
    ) -> VisualizationPlugin:
        registry = self._get_registry()
        if history_id is not None:
            history = self.history_manager.get_owned(history_id, trans.user, current_history=trans.history)
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
