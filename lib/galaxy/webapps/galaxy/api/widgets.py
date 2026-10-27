from galaxy.schema.widgets import (
    HistoryGraphParameters,
    PageParameters,
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
        description="Read-only graph of one workflow, with its information panel.",
        path="workflows/{workflow_id}",
        parameters_schema=WorkflowParameters.model_json_schema(),
    ),
]


@router.cbv
class FastAPIWidgets:
    @router.get(
        "/api/widgets",
        public=True,
        unstable=True,
        summary="Lists the widgets this Galaxy serves",
        description="Widgets are meant to be interactive, read-only views of single resources that respect "
        "Galaxy's authorization. Any origin may embed them unless `widgets_allowed_origins` is set. "
        "`/widgets/` serves the widgets app for any path, so a widget this Galaxy lacks still loads, "
        "showing only an error inside the page. Consumers check this list for the widgets and parameters "
        "an instance supports instead of hardcoding routes per Galaxy version.",
    )
    def index(self) -> list[Widget]:
        return WIDGETS
