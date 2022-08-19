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
    Any,
    Dict,
    List,
    Optional,
    Union,
)

from fastapi import (
    Depends,
    Query,
)

from galaxy import (
    exceptions,
    model,
)
from galaxy.managers import hdas
from galaxy.managers.context import (
    ProvidesHistoryContext,
    ProvidesUserContext,
)
from galaxy.managers.jobs import (
    JobLock,
    JobManager,
    JobSearch,
    summarize_destination_params,
    summarize_job_metrics,
    summarize_job_parameters,
)
from galaxy.schema.fields import EncodedDatabaseIdField
from galaxy.schema.schema import JobIndexSortByEnum
from galaxy.schema.types import OffsetNaiveDatetime
from galaxy.web import (
    expose_api,
    expose_api_anonymous,
    require_admin,
)
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
    JobIndexPayload,
    JobIndexViewEnum,
    JobsService,
)
from galaxy.work.context import WorkRequestContext

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
    description="If true, and requestor is an admin, will return external job id and user email. This is only available to admins.",
)

UserIdQueryParam: Optional[EncodedDatabaseIdField] = Query(
    default=None,
    title="User ID",
    description="an encoded user id to restrict query to, must be own id if not admin user",
)

ViewQueryParam: JobIndexViewEnum = Query(
    default="collection",
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

HistoryIdQueryParam: Optional[EncodedDatabaseIdField] = Query(
    default=None,
    title="History ID",
    description="Limit listing of jobs to those that match the history_id. If none, jobs from any history may be returned.",
)

WorkflowIdQueryParam: Optional[EncodedDatabaseIdField] = Query(
    default=None,
    title="Workflow ID",
    description="Limit listing of jobs to those that match the specified workflow ID. If none, jobs from any workflow (or from no workflows) may be returned.",
)

InvocationIdQueryParam: Optional[EncodedDatabaseIdField] = Query(
    default=None,
    title="Invocation ID",
    description="Limit listing of jobs to those that match the specified workflow invocation ID. If none, jobs from any workflow invocation (or from no workflows) may be returned.",
)

SortByQueryParam: JobIndexSortByEnum = Query(
    default=JobIndexSortByEnum.update_time,
    title="Sort By",
    description="Sort results by specified field.",
)

LimitQueryParam: int = Query(default=500, title="Limit", description="Maximum number of jobs to return.")

OffsetQueryParam: int = Query(
    default=0,
    title="Offset",
    description="Return jobs starting from this specified position. For example, if ``limit`` is set to 100 and ``offset`` to 200, jobs 200-299 will be returned.",
)

query_tags = [
    IndexQueryTag("user", "The user email of the user that executed the Job.", "u"),
    IndexQueryTag("tool_id", "The tool ID corresponding to the job.", "t"),
    IndexQueryTag("runner", "The job runner name used to execte the job.", "r", admin_only=True),
    IndexQueryTag("handler", "The job handler name used to execute the job.", "h", admin_only=True),
]

SearchQueryParam: Optional[str] = search_query_param(
    model_name="Job",
    tags=query_tags,
    free_text_fields=["user", "tool", "handler", "runner"],
)


@router.cbv
class FastAPIJobs:
    service: JobsService = depends(JobsService)

    @router.get("/api/jobs/{id}")
    def show(
        self,
        id: EncodedDatabaseIdField,
        trans: ProvidesUserContext = DependsOnTrans,
        full: Optional[bool] = False,
    ) -> Dict[str, Any]:
        """
        Return dictionary containing description of job data

        Parameters
        - id: ID of job to return
        - full: Return extra information ?
        """
        return self.service.show(trans, id, bool(full))

    @router.get("/api/jobs")
    def index(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        states: Optional[List[str]] = Depends(query_parameter_as_list(StateQueryParam)),
        user_details: bool = UserDetailsQueryParam,
        user_id: Optional[EncodedDatabaseIdField] = UserIdQueryParam,
        view: JobIndexViewEnum = ViewQueryParam,
        tool_ids: Optional[List[str]] = Depends(query_parameter_as_list(ToolIdQueryParam)),
        tool_ids_like: Optional[List[str]] = Depends(query_parameter_as_list(ToolIdLikeQueryParam)),
        date_range_min: Optional[Union[datetime, date]] = DateRangeMinQueryParam,
        date_range_max: Optional[Union[datetime, date]] = DateRangeMaxQueryParam,
        history_id: Optional[EncodedDatabaseIdField] = HistoryIdQueryParam,
        workflow_id: Optional[EncodedDatabaseIdField] = WorkflowIdQueryParam,
        invocation_id: Optional[EncodedDatabaseIdField] = InvocationIdQueryParam,
        order_by: JobIndexSortByEnum = SortByQueryParam,
        search: Optional[str] = SearchQueryParam,
        limit: int = LimitQueryParam,
        offset: int = OffsetQueryParam,
    ) -> List[Dict[str, Any]]:
        payload = JobIndexPayload(
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
            order_by=order_by,
            search=search,
            limit=limit,
            offset=offset,
        )
        return self.service.index(trans, payload)


class JobController(BaseGalaxyAPIController, UsesVisualizationMixin):
    job_manager = depends(JobManager)
    job_search = depends(JobSearch)
    hda_manager = depends(hdas.HDAManager)

    @expose_api
    def common_problems(self, trans: ProvidesUserContext, id, **kwd):
        """
        * GET /api/jobs/{id}/common_problems
            check inputs and job for common potential problems to aid in error reporting
        """
        job = self.__get_job(trans, id)
        seen_ids = set()
        has_empty_inputs = False
        has_duplicate_inputs = False
        for job_input_assoc in job.input_datasets:
            input_dataset_instance = job_input_assoc.dataset
            if input_dataset_instance is None:
                continue
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
        return {"has_empty_inputs": has_empty_inputs, "has_duplicate_inputs": has_duplicate_inputs}

    @expose_api
    def inputs(self, trans: ProvidesUserContext, id, **kwd):
        """
        GET /api/jobs/{id}/inputs

        returns input datasets created by job

        :type   id: string
        :param  id: Encoded job id

        :rtype:     dictionary
        :returns:   dictionary containing input dataset associations
        """
        job = self.__get_job(trans, id)
        return self.__dictify_associations(trans, job.input_datasets, job.input_library_datasets)

    @expose_api
    def outputs(self, trans: ProvidesUserContext, id, **kwd):
        """
        outputs( trans, id )
        * GET /api/jobs/{id}/outputs
            returns output datasets created by job

        :type   id: string
        :param  id: Encoded job id

        :rtype:     dictionary
        :returns:   dictionary containing output dataset associations
        """
        job = self.__get_job(trans, id)
        return self.__dictify_associations(trans, job.output_datasets, job.output_library_datasets)

    @expose_api
    def delete(self, trans: ProvidesUserContext, id, **kwd):
        """
        delete( trans, id )
        * Delete /api/jobs/{id}
            cancels specified job

        :type   id: string
        :param  id: Encoded job id
        :type   message: string
        :param  message: Stop message.
        """
        payload = kwd.get("payload") or {}
        job = self.__get_job(trans, id)
        message = payload.get("message", None)
        return self.job_manager.stop(job, message=message)

    @expose_api
    def resume(self, trans: ProvidesUserContext, id, **kwd):
        """
        * PUT /api/jobs/{id}/resume
            Resumes a paused job

        :type   id: string
        :param  id: Encoded job id

        :rtype:     dictionary
        :returns:   dictionary containing output dataset associations
        """
        job = self.__get_job(trans, id)
        if not job:
            raise exceptions.ObjectNotFound(f"Could not access job with id '{id}'")
        if job.state == job.states.PAUSED:
            job.resume()
        else:
            exceptions.RequestParameterInvalidException(f"Job with id '{job.tool_id}' is not paused")
        return self.__dictify_associations(trans, job.output_datasets, job.output_library_datasets)

    @expose_api_anonymous
    def metrics(self, trans: ProvidesUserContext, **kwd):
        """
        * GET /api/jobs/{job_id}/metrics
        * GET /api/datasets/{dataset_id}/metrics
            Return job metrics for specified job. Job accessibility checks are slightly
            different than dataset checks, so both methods are available.

        :type   job_id: string
        :param  job_id: Encoded job id

        :type   dataset_id: string
        :param  dataset_id: Encoded HDA or LDDA id

        :type   hda_ldda: string
        :param  hda_ldda: hda if dataset_id is an HDA id (default), ldda if
                          it is an ldda id.

        :rtype:     list
        :returns:   list containing job metrics
        """
        job = self.__get_job(trans, **kwd)
        return summarize_job_metrics(trans, job)

    @require_admin
    @expose_api
    def destination_params(self, trans: ProvidesUserContext, **kwd):
        """
        * GET /api/jobs/{job_id}/destination_params
            Return destination parameters for specified job.

        :type   job_id: string
        :param  job_id: Encoded job id

        :rtype:     list
        :returns:   list containing job destination parameters
        """
        job = self.__get_job(trans, **kwd)
        return summarize_destination_params(trans, job)

    @expose_api_anonymous
    def parameters_display(self, trans: ProvidesUserContext, **kwd):
        """
        * GET /api/jobs/{job_id}/parameters_display
        * GET /api/datasets/{dataset_id}/parameters_display

            Resolve parameters as a list for nested display. More client logic
            here than is ideal but it is hard to reason about tool parameter
            types on the client relative to the server. Job accessibility checks
            are slightly different than dataset checks, so both methods are
            available.

            This API endpoint is unstable and tied heavily to Galaxy's JS client code,
            this endpoint will change frequently.

        :type   job_id: string
        :param  job_id: Encoded job id

        :type   dataset_id: string
        :param  dataset_id: Encoded HDA or LDDA id

        :type   hda_ldda: string
        :param  hda_ldda: hda if dataset_id is an HDA id (default), ldda if
                          it is an ldda id.

        :rtype:     list
        :returns:   job parameters for for display
        """
        job = self.__get_job(trans, **kwd)
        return summarize_job_parameters(trans, job)

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
            raise exceptions.ObjectNotFound(f"Could not access job with id '{id}'")
        tool = self.app.toolbox.get_tool(job.tool_id, kwd.get("tool_version") or job.tool_version)
        if tool is None:
            raise exceptions.ObjectNotFound("Requested tool not found")
        if not tool.is_workflow_compatible:
            raise exceptions.ConfigDoesNotAllowException(f"Tool '{job.tool_id}' cannot be rerun.")
        return tool.to_json(trans, {}, job=job)

    def __dictify_associations(self, trans, *association_lists):
        rval = []
        for association_list in association_lists:
            rval.extend(self.__dictify_association(trans, a) for a in association_list)
        return rval

    def __dictify_association(self, trans, job_dataset_association):
        dataset_dict = None
        dataset = job_dataset_association.dataset
        if dataset:
            if isinstance(dataset, model.HistoryDatasetAssociation):
                dataset_dict = dict(src="hda", id=trans.security.encode_id(dataset.id))
            else:
                dataset_dict = dict(src="ldda", id=trans.security.encode_id(dataset.id))
        return dict(name=job_dataset_association.name, dataset=dataset_dict)

    def __get_job(self, trans, job_id=None, dataset_id=None, **kwd):
        if job_id is not None:
            decoded_job_id = self.decode_id(job_id)
            return self.job_manager.get_accessible_job(trans, decoded_job_id)
        else:
            hda_ldda = kwd.get("hda_ldda", "hda")
            # Following checks dataset accessible
            dataset_instance = self.get_hda_or_ldda(trans, hda_ldda=hda_ldda, dataset_id=dataset_id)
            return dataset_instance.creating_job

    @expose_api
    def create(self, trans: ProvidesUserContext, payload, **kwd):
        """See the create method in tools.py in order to submit a job."""
        raise exceptions.NotImplemented("Please POST to /api/tools instead.")

    @expose_api
    def search(self, trans: ProvidesHistoryContext, payload: dict, **kwd):
        """
        search( trans, payload )
        * POST /api/jobs/search:
            return jobs for current user

        :type   payload: dict
        :param  payload: Dictionary containing description of requested job. This is in the same format as
            a request to POST /apt/tools would take to initiate a job

        :rtype:     list
        :returns:   list of dictionaries containing summary job information of the jobs that match the requested job run

        This method is designed to scan the list of previously run jobs and find records of jobs that had
        the exact some input parameters and datasets. This can be used to minimize the amount of repeated work, and simply
        recycle the old results.
        """
        tool_id = payload.get("tool_id")
        if tool_id is None:
            raise exceptions.RequestParameterMissingException("No tool id")
        tool = trans.app.toolbox.get_tool(tool_id)
        if tool is None:
            raise exceptions.ObjectNotFound("Requested tool not found")
        if "inputs" not in payload:
            raise exceptions.RequestParameterMissingException("No inputs defined")
        inputs = payload.get("inputs", {})
        # Find files coming in as multipart file data and add to inputs.
        for k, v in payload.items():
            if k.startswith("files_") or k.startswith("__files_"):
                inputs[k] = v
        request_context = WorkRequestContext(app=trans.app, user=trans.user, history=trans.history)
        all_params, all_errors, _, _ = tool.expand_incoming(
            trans=trans, incoming=inputs, request_context=request_context
        )
        if any(all_errors):
            return []
        params_dump = [tool.params_to_strings(param, self.app, nested=True) for param in all_params]
        jobs = []
        for param_dump, param in zip(params_dump, all_params):
            job = self.job_search.by_tool_input(
                trans=trans,
                tool_id=tool_id,
                tool_version=tool.version,
                param=param,
                param_dump=param_dump,
                job_state=payload.get("state"),
            )
            if job:
                jobs.append(job)
        return [self.encode_all_ids(trans, single_job.to_dict("element"), True) for single_job in jobs]

    @expose_api_anonymous
    def error(self, trans: ProvidesUserContext, id, payload, **kwd):
        """
        error( trans, id )
        * POST /api/jobs/{id}/error
            submits a bug report via the API.

        :type   id: string
        :param  id: Encoded job id

        :rtype:     dictionary
        :returns:   dictionary containing information regarding where the error report was sent.
        """
        # Get dataset on which this error was triggered
        dataset_id = payload.get("dataset_id")
        if not dataset_id:
            raise exceptions.RequestParameterMissingException("No dataset_id")
        decoded_dataset_id = self.decode_id(dataset_id)
        dataset = self.hda_manager.get_accessible(decoded_dataset_id, trans.user)

        # Get job
        job = self.__get_job(trans, id)
        if dataset.creating_job.id != job.id:
            raise exceptions.RequestParameterInvalidException("dataset_id was not created by job_id")
        tool = trans.app.toolbox.get_tool(job.tool_id, tool_version=job.tool_version) or None
        email = payload.get("email")
        if not email and not trans.anonymous:
            email = trans.user.email
        messages = trans.app.error_reports.default_error_plugin.submit_report(
            dataset=dataset,
            job=job,
            tool=tool,
            user_submission=True,
            user=trans.user,
            email=email,
            message=payload.get("message"),
        )

        return {"messages": messages}

    @require_admin
    @expose_api
    def show_job_lock(self, trans: ProvidesUserContext, **kwd):
        """
        * GET /api/job_lock
            return boolean indicating if job lock active.
        """
        return self.job_manager.job_lock()

    @require_admin
    @expose_api
    def update_job_lock(self, trans: ProvidesUserContext, payload, **kwd):
        """
        * PUT /api/job_lock
            return boolean indicating if job lock active.
        """
        active = payload.get("active")
        job_lock = JobLock(active=active)
        return self.job_manager.update_job_lock(job_lock)
