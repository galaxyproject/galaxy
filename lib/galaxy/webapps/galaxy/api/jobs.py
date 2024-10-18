"""
API operations on a jobs.

.. seealso:: :class:`galaxy.model.Jobs`
"""

import logging
from datetime import (
    date,
    datetime,
)
from typing import (
    List,
    Optional,
    Union,
)

from fastapi import (
    Body,
    Depends,
    Path,
    Query,
)
from typing_extensions import Annotated

from galaxy import exceptions
from galaxy.managers.context import (
    ProvidesHistoryContext,
    ProvidesUserContext,
)
from galaxy.managers.jobs import (
    JobManager,
    summarize_destination_params,
    summarize_job_metrics,
    summarize_job_parameters,
)
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.schema.jobs import (
    DeleteJobPayload,
    EncodedJobDetails,
    JobDestinationParams,
    JobDisplayParametersSummary,
    JobErrorSummary,
    JobInputAssociation,
    JobInputSummary,
    JobOutputAssociation,
    JobOutputCollectionAssociation,
    ReportJobErrorPayload,
    SearchJobsPayload,
    ShowFullJobResponse,
)
from galaxy.schema.schema import (
    DatasetSourceType,
    JobIndexSortByEnum,
    JobMetric,
    JobSummary,
)
from galaxy.schema.types import OffsetNaiveDatetime
from galaxy.web import expose_api_anonymous
from galaxy.webapps.base.controller import UsesVisualizationMixin
from galaxy.webapps.galaxy.api import (
    BaseGalaxyAPIController,
    depends,
    DependsOnTrans,
    IndexQueryTag,
    Router,
    search_query_param,
)
from galaxy.webapps.galaxy.api.common import query_parameter_as_list
from galaxy.webapps.galaxy.services.jobs import (
    JobCreateResponse,
    JobIndexPayload,
    JobIndexViewEnum,
    JobRequest,
    JobsService,
)
from galaxy.work.context import proxy_work_context_for_history
from .tools import validate_not_protected

log = logging.getLogger(__name__)

router = Router(tags=["jobs"])


StateQueryParam = Query(
    default=None,
    alias="state",
    title="States",
    description="A list or comma-separated list of states to filter job query on. If unspecified, jobs of any state may be returned.",
)

UserDetailsQueryParam: bool = Query(
    default=False,
    title="Include user details",
    description="If true, and requester is an admin, will return external job id and user email. This is only available to admins.",
)

UserIdQueryParam: Optional[DecodedDatabaseIdField] = Query(
    default=None,
    title="User ID",
    description="an encoded user id to restrict query to, must be own id if not admin user",
)

ViewQueryParam: JobIndexViewEnum = Query(
    default=JobIndexViewEnum.collection,
    title="View",
    description="Determines columns to return. Defaults to 'collection'.",
)


ToolIdQueryParam = Query(
    default=None,
    alias="tool_id",
    title="Tool ID(s)",
    description="Limit listing of jobs to those that match one of the included tool_ids. If none, all are returned",
)


ToolIdLikeQueryParam = Query(
    default=None,
    alias="tool_id_like",
    title="Tool ID Pattern(s)",
    description="Limit listing of jobs to those that match one of the included tool ID sql-like patterns. If none, all are returned",
)

DateRangeMinQueryParam: Optional[Union[OffsetNaiveDatetime, date]] = Query(
    default=None,
    title="Date Range Minimum",
    description="Limit listing of jobs to those that are updated after specified date (e.g. '2014-01-01')",
)

DateRangeMaxQueryParam: Optional[Union[OffsetNaiveDatetime, date]] = Query(
    default=None,
    title="Date Range Maximum",
    description="Limit listing of jobs to those that are updated before specified date (e.g. '2014-01-01')",
)

HistoryIdQueryParam: Optional[DecodedDatabaseIdField] = Query(
    default=None,
    title="History ID",
    description="Limit listing of jobs to those that match the history_id. If none, jobs from any history may be returned.",
)

WorkflowIdQueryParam: Optional[DecodedDatabaseIdField] = Query(
    default=None,
    title="Workflow ID",
    description="Limit listing of jobs to those that match the specified workflow ID. If none, jobs from any workflow (or from no workflows) may be returned.",
)

InvocationIdQueryParam: Optional[DecodedDatabaseIdField] = Query(
    default=None,
    title="Invocation ID",
    description="Limit listing of jobs to those that match the specified workflow invocation ID. If none, jobs from any workflow invocation (or from no workflows) may be returned.",
)

ImplicitCollectionJobsIdQueryParam: Optional[DecodedDatabaseIdField] = Query(
    default=None,
    title="Implicit Collection Jobs ID",
    description="Limit listing of jobs to those that match the specified implicit collection job ID. If none, jobs from any implicit collection execution (or from no implicit collection execution) may be returned.",
)

ToolRequestIdQueryParam: Optional[DecodedDatabaseIdField] = Query(
    default=None,
    title="Tool Request ID",
    description="Limit listing of jobs to those that were created from the supplied tool request ID. If none, jobs from any tool request (or from no workflows) may be returned.",
)

SortByQueryParam: JobIndexSortByEnum = Query(
    default=JobIndexSortByEnum.update_time,
    title="Sort By",
    description="Sort results by specified field.",
)

LimitQueryParam: int = Query(default=500, ge=1, title="Limit", description="Maximum number of jobs to return.")

OffsetQueryParam: int = Query(
    default=0,
    ge=0,
    title="Offset",
    description="Return jobs starting from this specified position. For example, if ``limit`` is set to 100 and ``offset`` to 200, jobs 200-299 will be returned.",
)

query_tags = [
    IndexQueryTag("user", "The user email of the user that executed the Job.", "u"),
    IndexQueryTag("tool_id", "The tool ID corresponding to the job.", "t"),
    IndexQueryTag("runner", "The job runner name used to execute the job.", "r", admin_only=True),
    IndexQueryTag("handler", "The job handler name used to execute the job.", "h", admin_only=True),
]

SearchQueryParam: Optional[str] = search_query_param(
    model_name="Job",
    tags=query_tags,
    free_text_fields=["user", "tool", "handler", "runner"],
)

FullShowQueryParam: Optional[bool] = Query(title="Full show", description="Show extra information.")
DeprecatedHdaLddaQueryParam: Optional[DatasetSourceType] = Query(
    deprecated=True,
    title="HDA or LDDA",
    description="Whether this dataset belongs to a history (HDA) or a library (LDDA).",
)
HdaLddaQueryParam: DatasetSourceType = Query(
    title="HDA or LDDA",
    description="Whether this dataset belongs to a history (HDA) or a library (LDDA).",
)


JobIdPathParam = Annotated[DecodedDatabaseIdField, Path(title="Job ID", description="The ID of the job")]
DatasetIdPathParam = Annotated[DecodedDatabaseIdField, Path(title="Dataset ID", description="The ID of the dataset")]

ReportErrorBody = Body(default=..., title="Report error", description="The values to report an Error")
SearchJobBody = Body(default=..., title="Search job", description="The values to search an Job")
DeleteJobBody = Body(title="Delete/cancel job", description="The values to delete/cancel a job")


@router.cbv
class FastAPIJobs:
    service: JobsService = depends(JobsService)

    @router.post("/api/jobs")
    def create(
        self, trans: ProvidesHistoryContext = DependsOnTrans, job_request: JobRequest = Body(...)
    ) -> JobCreateResponse:
        validate_not_protected(job_request.tool_id)
        return self.service.create(trans, job_request)

    @router.get("/api/jobs")
    def index(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        states: Optional[List[str]] = Depends(query_parameter_as_list(StateQueryParam)),
        user_details: bool = UserDetailsQueryParam,
        user_id: Optional[DecodedDatabaseIdField] = UserIdQueryParam,
        view: JobIndexViewEnum = ViewQueryParam,
        tool_ids: Optional[List[str]] = Depends(query_parameter_as_list(ToolIdQueryParam)),
        tool_ids_like: Optional[List[str]] = Depends(query_parameter_as_list(ToolIdLikeQueryParam)),
        date_range_min: Optional[Union[datetime, date]] = DateRangeMinQueryParam,
        date_range_max: Optional[Union[datetime, date]] = DateRangeMaxQueryParam,
        history_id: Optional[DecodedDatabaseIdField] = HistoryIdQueryParam,
        workflow_id: Optional[DecodedDatabaseIdField] = WorkflowIdQueryParam,
        invocation_id: Optional[DecodedDatabaseIdField] = InvocationIdQueryParam,
        implicit_collection_jobs_id: Optional[DecodedDatabaseIdField] = ImplicitCollectionJobsIdQueryParam,
        tool_request_id: Optional[DecodedDatabaseIdField] = ToolRequestIdQueryParam,
        order_by: JobIndexSortByEnum = SortByQueryParam,
        search: Optional[str] = SearchQueryParam,
        limit: int = LimitQueryParam,
        offset: int = OffsetQueryParam,
    ) -> List[Union[ShowFullJobResponse, EncodedJobDetails, JobSummary]]:
        payload = JobIndexPayload.model_construct(
            states=states,
            user_details=user_details,
            user_id=user_id,
            view=view,
            tool_ids=tool_ids,
            tool_ids_like=tool_ids_like,
            date_range_min=date_range_min,
            date_range_max=date_range_max,
            history_id=history_id,
            workflow_id=workflow_id,
            invocation_id=invocation_id,
            implicit_collection_jobs_id=implicit_collection_jobs_id,
            tool_request_id=tool_request_id,
            order_by=order_by,
            search=search,
            limit=limit,
            offset=offset,
        )
        return self.service.index(trans, payload)

    @router.get(
        "/api/jobs/{job_id}/common_problems",
        name="check_common_problems",
        summary="Check inputs and job for common potential problems to aid in error reporting",
    )
    def common_problems(
        self,
        job_id: JobIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> JobInputSummary:
        job = self.service.get_job(trans=trans, job_id=job_id)
        seen_ids = set()
        has_empty_inputs = False
        has_duplicate_inputs = False
        for job_input_assoc in job.input_datasets:
            input_dataset_instance = job_input_assoc.dataset
            if input_dataset_instance is None:
                continue  # type:ignore[unreachable]  # TODO if job_input_assoc.dataset is indeed never None, remove the above check
            if input_dataset_instance.get_total_size() == 0:
                has_empty_inputs = True
            input_instance_id = input_dataset_instance.id
            if input_instance_id in seen_ids:
                has_duplicate_inputs = True
            else:
                seen_ids.add(input_instance_id)
        # TODO: check percent of failing jobs around a window on job.update_time for handler - report if high.
        # TODO: check percent of failing jobs around a window on job.update_time for destination_id - report if high.
        # TODO: sniff inputs (add flag to allow checking files?)
        return JobInputSummary(has_empty_inputs=has_empty_inputs, has_duplicate_inputs=has_duplicate_inputs)

    @router.put(
        "/api/jobs/{job_id}/resume",
        name="resume_paused_job",
        summary="Resumes a paused job.",
    )
    def resume(
        self,
        job_id: JobIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> List[JobOutputAssociation]:
        job = self.service.get_job(trans, job_id=job_id)
        if not job:
            raise exceptions.ObjectNotFound("Could not access job with the given id")
        if job.state == job.states.PAUSED:
            job.resume()
        else:
            exceptions.RequestParameterInvalidException(f"Job with id '{job.tool_id}' is not paused")
        # Maybe just return 202 ? What's the point of this ?
        associations = self.service.dictify_associations(trans, job.output_datasets, job.output_library_datasets)
        output_associations = []
        for association in associations:
            output_associations.append(JobOutputAssociation(name=association.name, dataset=association.dataset))
        return output_associations

    @router.post(
        "/api/jobs/{job_id}/error",
        name="report_error",
        summary="Submits a bug report via the API.",
    )
    def error(
        self,
        payload: Annotated[ReportJobErrorPayload, ReportErrorBody],
        job_id: JobIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> JobErrorSummary:
        # Get dataset on which this error was triggered
        dataset_id = payload.dataset_id
        dataset = self.service.hda_manager.get_accessible(id=dataset_id, user=trans.user)
        # Get job
        job = self.service.get_job(trans, job_id)
        if not dataset.creating_job or dataset.creating_job.id != job.id:
            raise exceptions.RequestParameterInvalidException("dataset_id was not created by job_id")
        tool = trans.app.toolbox.get_tool(job.tool_id, tool_version=job.tool_version) or None
        email = payload.email
        if not email and not trans.anonymous:
            email = trans.user.email
        messages = trans.app.error_reports.default_error_plugin.submit_report(
            dataset=dataset,
            job=job,
            tool=tool,
            user_submission=True,
            user=trans.user,
            email=email,
            message=payload.message,
        )
        return JobErrorSummary(messages=messages)

    @router.get(
        "/api/jobs/{job_id}/inputs",
        name="get_inputs",
        summary="Returns input datasets created by a job.",
    )
    def inputs(
        self,
        job_id: JobIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> List[JobInputAssociation]:
        job = self.service.get_job(trans=trans, job_id=job_id)
        associations = self.service.dictify_associations(trans, job.input_datasets, job.input_library_datasets)
        input_associations = []
        for association in associations:
            input_associations.append(JobInputAssociation(name=association.name, dataset=association.dataset))
        return input_associations

    @router.get(
        "/api/jobs/{job_id}/outputs",
        name="get_outputs",
        summary="Returns output datasets created by a job.",
    )
    def outputs(
        self,
        job_id: JobIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> List[Union[JobOutputAssociation, JobOutputCollectionAssociation]]:
        job = self.service.get_job(trans=trans, job_id=job_id)
        associations = self.service.dictify_associations(trans, job.output_datasets, job.output_library_datasets)
        output_associations: List[Union[JobOutputAssociation, JobOutputCollectionAssociation]] = []
        for association in associations:
            output_associations.append(JobOutputAssociation(name=association.name, dataset=association.dataset))

        output_associations.extend(self.service.dictify_output_collection_associations(trans, job))
        return output_associations

    @router.get(
        "/api/jobs/{job_id}/parameters_display",
        name="resolve_parameters_display",
        summary="Resolve parameters as a list for nested display.",
    )
    def parameters_display_by_job(
        self,
        job_id: JobIdPathParam,
        hda_ldda: Annotated[Optional[DatasetSourceType], DeprecatedHdaLddaQueryParam] = DatasetSourceType.hda,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> JobDisplayParametersSummary:
        """
        Resolve parameters as a list for nested display.
        This API endpoint is unstable and tied heavily to Galaxy's JS client code,
        this endpoint will change frequently.
        """
        hda_ldda_str = hda_ldda or "hda"
        job = self.service.get_job(trans, job_id=job_id, hda_ldda=hda_ldda_str)
        return summarize_job_parameters(trans, job)

    @router.get(
        "/api/datasets/{dataset_id}/parameters_display",
        name="resolve_parameters_display",
        summary="Resolve parameters as a list for nested display.",
        deprecated=True,
    )
    def parameters_display_by_dataset(
        self,
        dataset_id: DatasetIdPathParam,
        hda_ldda: Annotated[DatasetSourceType, HdaLddaQueryParam] = DatasetSourceType.hda,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> JobDisplayParametersSummary:
        """
        Resolve parameters as a list for nested display.
        This API endpoint is unstable and tied heavily to Galaxy's JS client code,
        this endpoint will change frequently.
        """
        job = self.service.get_job(trans, dataset_id=dataset_id, hda_ldda=hda_ldda)
        return summarize_job_parameters(trans, job)

    @router.get(
        "/api/jobs/{job_id}/metrics",
        name="get_metrics",
        summary="Return job metrics for specified job.",
    )
    def metrics_by_job(
        self,
        job_id: JobIdPathParam,
        hda_ldda: Annotated[Optional[DatasetSourceType], DeprecatedHdaLddaQueryParam] = DatasetSourceType.hda,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> List[Optional[JobMetric]]:
        hda_ldda_str = hda_ldda or "hda"
        job = self.service.get_job(trans, job_id=job_id, hda_ldda=hda_ldda_str)
        return [JobMetric(**metric) for metric in summarize_job_metrics(trans, job)]

    @router.get(
        "/api/datasets/{dataset_id}/metrics",
        name="get_metrics",
        summary="Return job metrics for specified job.",
        deprecated=True,
    )
    def metrics_by_dataset(
        self,
        dataset_id: DatasetIdPathParam,
        hda_ldda: Annotated[DatasetSourceType, HdaLddaQueryParam] = DatasetSourceType.hda,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> List[Optional[JobMetric]]:
        job = self.service.get_job(trans, dataset_id=dataset_id, hda_ldda=hda_ldda)
        return [JobMetric(**metric) for metric in summarize_job_metrics(trans, job)]

    @router.get(
        "/api/jobs/{job_id}/destination_params",
        name="destination_params_job",
        summary="Return destination parameters for specified job.",
        require_admin=True,
    )
    def destination_params(
        self,
        job_id: JobIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> JobDestinationParams:
        job = self.service.get_job(trans, job_id=job_id)
        return JobDestinationParams(**summarize_destination_params(trans, job))

    @router.post(
        "/api/jobs/search",
        name="search_jobs",
        summary="Return jobs for current user",
    )
    def search(
        self,
        payload: Annotated[SearchJobsPayload, SearchJobBody],
        trans: ProvidesHistoryContext = DependsOnTrans,
    ) -> List[EncodedJobDetails]:
        """
        This method is designed to scan the list of previously run jobs and find records of jobs that had
        the exact some input parameters and datasets. This can be used to minimize the amount of repeated work, and simply
        recycle the old results.
        """
        tool_id = payload.tool_id

        tool = trans.app.toolbox.get_tool(tool_id)
        if tool is None:
            raise exceptions.ObjectNotFound("Requested tool not found")
        inputs = payload.inputs
        # Find files coming in as multipart file data and add to inputs.
        for k, v in payload.__annotations__.items():
            if k.startswith("files_") or k.startswith("__files_"):
                inputs[k] = v
        request_context = proxy_work_context_for_history(trans)
        all_params, all_errors, _, _ = tool.expand_incoming(request_context, incoming=inputs)
        if any(all_errors):
            return []
        params_dump = [tool.params_to_strings(param, trans.app, nested=True) for param in all_params]
        jobs = []
        for param_dump, param in zip(params_dump, all_params):
            job = self.service.job_search.by_tool_input(
                trans=trans,
                tool_id=tool_id,
                tool_version=tool.version,
                param=param,
                param_dump=param_dump,
                job_state=payload.state,
            )
            if job:
                jobs.append(job)
        return [EncodedJobDetails(**single_job.to_dict("element")) for single_job in jobs]

    @router.get(
        "/api/jobs/{job_id}",
        name="show_job",
        summary="Return dictionary containing description of job data.",
    )
    def show(
        self,
        job_id: JobIdPathParam,
        full: Annotated[Optional[bool], FullShowQueryParam] = False,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> Union[ShowFullJobResponse, EncodedJobDetails]:
        if full:
            return ShowFullJobResponse(**self.service.show(trans, job_id, bool(full)))
        else:
            return EncodedJobDetails(**self.service.show(trans, job_id, bool(full)))

    @router.delete(
        "/api/jobs/{job_id}",
        name="cancel_job",
        summary="Cancels specified job",
    )
    def delete(
        self,
        job_id: JobIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
        payload: Annotated[Optional[DeleteJobPayload], DeleteJobBody] = None,
    ) -> bool:
        job = self.service.get_job(trans=trans, job_id=job_id)
        if payload:
            message = payload.message
        else:
            message = None
        return self.service.job_manager.stop(job, message=message)


class JobController(BaseGalaxyAPIController, UsesVisualizationMixin):
    job_manager = depends(JobManager)

    @expose_api_anonymous
    def build_for_rerun(self, trans: ProvidesHistoryContext, id, **kwd):
        """
        * GET /api/jobs/{id}/build_for_rerun
            returns a tool input/param template prepopulated with this job's
            information, suitable for rerunning or rendering parameters of the
            job.

        :type   id: string
        :param  id: Encoded job id

        :rtype:     dictionary
        :returns:   dictionary containing output dataset associations
        """

        job = self.__get_job(trans, id)
        if not job:
            raise exceptions.ObjectNotFound("Could not access job with the given id")
        tool = self.app.toolbox.get_tool(job.tool_id, kwd.get("tool_version") or job.tool_version)
        if tool is None:
            raise exceptions.ObjectNotFound("Requested tool not found")
        if not tool.is_workflow_compatible:
            raise exceptions.ConfigDoesNotAllowException(f"Tool '{job.tool_id}' cannot be rerun.")
        return tool.to_json(trans, {}, job=job)

    def __get_job(self, trans, job_id=None, dataset_id=None, **kwd):
        if job_id is not None:
            decoded_job_id = self.decode_id(job_id)
            return self.job_manager.get_accessible_job(trans, decoded_job_id)
        else:
            hda_ldda = kwd.get("hda_ldda", "hda")
            # Following checks dataset accessible
            dataset_instance = self.get_hda_or_ldda(trans, hda_ldda=hda_ldda, dataset_id=dataset_id)
            return dataset_instance.creating_job
