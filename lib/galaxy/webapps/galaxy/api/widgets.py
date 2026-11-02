import re
from typing import Any

from galaxy import exceptions
from galaxy.managers.context import ProvidesAppContext
from galaxy.managers.pages import PageManager
from galaxy.managers.sharable import SharableModelManager
from galaxy.managers.workflows import WorkflowsManager
from galaxy.schema.widgets import (
    HistoryGraphParameters,
    PageParameters,
    VisualizationParameters,
    Widget,
    WorkflowParameters,
)
from . import Router

router = Router(tags=["widgets"])

WIDGETS = [
    Widget(
        id="history_graph",
        name="History graph",
        description="Provenance graph of one history: its datasets, collections and the tool runs connecting them.",
        path="histories/{history_id}/graph",
        parameters_schema=HistoryGraphParameters.model_json_schema(),
    ),
    Widget(
        id="page",
        name="Page",
        description="Rendered content of one page.",
        path="pages/{page_id}",
        parameters_schema=PageParameters.model_json_schema(),
    ),
    Widget(
        id="workflow",
        name="Workflow",
        description="Graph of one workflow, with its information panel.",
        path="workflows/{workflow_id}",
        parameters_schema=WorkflowParameters.model_json_schema(),
    ),
    Widget(
        id="visualization",
        name="Visualization",
        description="Saved visualization, rendered by its plugin.",
        path="visualizations/{visualization_id}",
        parameters_schema=VisualizationParameters.model_json_schema(),
    ),
]

PUBLIC_WIDGET_MANAGERS: dict[str, type[SharableModelManager[Any]]] = {"page": PageManager, "workflow": WorkflowsManager}

PUBLIC_WIDGETS = [
    (re.compile("/widgets/" + re.sub(r"\{\w+\}", "([0-9a-f]+)", widget.path) + "/?"), PUBLIC_WIDGET_MANAGERS[widget.id])
    for widget in WIDGETS
    if widget.id in PUBLIC_WIDGET_MANAGERS
]


def is_public_widget(trans: ProvidesAppContext, path: str) -> bool:
    public = False
    for pattern, public_manager in PUBLIC_WIDGETS:
        if match := pattern.fullmatch(path):
            manager = trans.app[public_manager]
            try:
                item = trans.sa_session.get(manager.model_class, trans.security.decode_id(match.group(1)))
            except exceptions.MalformedId:
                item = None
            public = bool(item and not item.deleted and manager.is_accessible(item, None))
    return public


@router.cbv
class FastAPIWidgets:
    @router.get(
        "/api/widgets",
        public=True,
        unstable=True,
        summary="Lists the widgets this Galaxy serves",
        description="Widgets are interactive views of single resources that respect Galaxy's authorization. "
        "Hiding actions in a widget is a presentation choice, not an access control. Any origin may embed "
        "widgets that support public embedding while their resource is published or accessible via link; other "
        "widgets only Galaxy itself and the origins in `widgets_allowed_origins`. `/widgets/` serves the widgets "
        "app for any path, so a widget this Galaxy lacks still loads, showing only an error inside the page. "
        "Consumers check this list for the widgets and parameters an instance supports instead of hardcoding "
        "routes per Galaxy version.",
    )
    def index(self) -> list[Widget]:
        return WIDGETS
