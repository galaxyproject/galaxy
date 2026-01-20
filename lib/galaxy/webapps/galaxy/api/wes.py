"""GA4GH WES (Workflow Execution Service) API endpoints."""

import logging
from typing import (
    Annotated,
    Optional,
)

from fastapi import (
    File,
    Form,
    Path,
    Query,
    Request,
    UploadFile,
)

from galaxy.managers.context import ProvidesUserContext
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.schema.wes import (
    RunId,
    RunListResponse,
    RunLog,
    RunStatus,
    ServiceInfo,
    TaskListResponse,
    TaskLog,
)
from galaxy.webapps.galaxy.services.wes import WesService
from galaxy.work.context import SessionRequestContext
from . import (
    depends,
    DependsOnTrans,
    Router,
)

log = logging.getLogger(__name__)
router = Router(tags=["wes"])

RunIdParam = Annotated[
    DecodedDatabaseIdField,
    Path(
        title="Workflow Invocation ID",
    ),
]
TaskIdParam = Annotated[
    str,
    Path(
        title="Task ID",
        description="Task identifier: step order_index, or order_index.job_index for collection mapping jobs",
    ),
]
PageTokenParam: str = Query(None, title="Page Token", description="Token for pagination")
PageSizeParam: int = Query(10, title="Page Size", description="Number of results per page", ge=1, le=100)

WES_SERVICE_NAME = "Galaxy WES API"
WES_SERVICE_DESCRIPTION = "Executes Galaxy workflows according to the GA4GH WES specification"


@router.cbv
class WesApi:
    service: WesService = depends(WesService)

    @router.get("/ga4gh/wes/v1/service-info", public=True)
    def service_info(self, request: Request, trans: ProvidesUserContext = DependsOnTrans) -> ServiceInfo:
        """Get WES service information."""
        return self.service.service_info(trans, str(request.url))

    @router.post("/ga4gh/wes/v1/runs")
    def submit_run(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        workflow_params: Optional[str] = Form(None),
        workflow_type: str = Form(...),
        workflow_type_version: str = Form(...),
        workflow_url: Optional[str] = Form(None),
        workflow_engine_parameters: Optional[str] = Form(None),
        workflow_engine: Optional[str] = Form(None),
        workflow_engine_version: Optional[str] = Form(None),
        tags: Optional[str] = Form(None),
        workflow_attachment: Optional[UploadFile] = File(None),
    ) -> RunId:
        """Submit a new workflow run.

        Accepts multipart/form-data with workflow and parameters.
        """
        return self.service.submit_run(
            trans=trans,
            workflow_params=workflow_params,
            workflow_type=workflow_type,
            workflow_type_version=workflow_type_version,
            workflow_url=workflow_url,
            workflow_engine_parameters=workflow_engine_parameters,
            workflow_engine=workflow_engine,
            workflow_engine_version=workflow_engine_version,
            tags=tags,
            workflow_attachment=workflow_attachment,
        )

    @router.get("/ga4gh/wes/v1/runs")
    def list_runs(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        page_size: int = PageSizeParam,
        page_token: str = PageTokenParam,
    ) -> RunListResponse:
        """List workflow runs."""
        return self.service.list_runs(trans, page_size, page_token)

    @router.get("/ga4gh/wes/v1/runs/{run_id}")
    def get_run(
        self,
        run_id: RunIdParam,
        trans: SessionRequestContext = DependsOnTrans,
    ) -> RunLog:
        """Get workflow run details."""
        assert isinstance(run_id, int)
        return self.service.get_run(trans, run_id)

    @router.get("/ga4gh/wes/v1/runs/{run_id}/status")
    def get_run_status(
        self,
        run_id: RunIdParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> RunStatus:
        """Get workflow run status."""
        return self.service.get_run_status(trans, run_id)

    @router.post("/ga4gh/wes/v1/runs/{run_id}/cancel")
    def cancel_run(
        self,
        run_id: RunIdParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> RunId:
        """Cancel a workflow run."""
        return self.service.cancel_run(trans, run_id)

    @router.get("/ga4gh/wes/v1/runs/{run_id}/tasks")
    def get_run_tasks(
        self,
        run_id: RunIdParam,
        trans: ProvidesUserContext = DependsOnTrans,
        page_size: int = PageSizeParam,
        page_token: str = PageTokenParam,
    ) -> TaskListResponse:
        """Get paginated list of tasks for a workflow run."""
        assert isinstance(run_id, int)
        return self.service.get_run_tasks(trans, run_id, page_size, page_token)

    @router.get("/ga4gh/wes/v1/runs/{run_id}/tasks/{task_id}")
    def get_run_task(
        self,
        run_id: RunIdParam,
        task_id: TaskIdParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> TaskLog:
        """Get details for a specific task.

        Task ID format: order_index or order_index.job_index for collection mapping jobs.
        """
        assert isinstance(run_id, int)
        return self.service.get_run_task(trans, run_id, task_id)
