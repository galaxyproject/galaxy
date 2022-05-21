"""
API operations on a jobs.

.. seealso:: :class:`galaxy.model.Jobs`
"""

import logging
from enum import Enum
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from fastapi import Query
from sqlalchemy import or_

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
    view_show_job,
)
from galaxy.schema.fields import EncodedDatabaseIdField
from galaxy.util import listify
from galaxy.web import (
    expose_api,
    expose_api_anonymous,
    require_admin,
)
from galaxy.webapps.base.controller import UsesVisualizationMixin
from galaxy.work.context import WorkRequestContext
from . import (
    BaseGalaxyAPIController,
    depends,
    DependsOnTrans,
    Router,
)

log = logging.getLogger(__name__)

router = Router(tags=["jobs"])


class JobIndexViewEnum(str, Enum):
    collection = "collection"
    admin_job_list = "admin_job_list"


class JobIndexSortByEnum(str, Enum):
    create_time = "create_time"
    update_time = "update_time"


StateQueryParam: Optional[str] = Query(
    default=None,
    title="States",
    description="Comma-separated list of states to filter job query on. If unspecified, jobs of any state may be returned.",
)

UserDetailsQueryParam: bool = Query(
    default=False,
    title="Include user details",
    description="If true, and requestor is an admin, will return external job id and user email.",
)

UserIdQueryParam: Optional[str] = Query(
    default=None,
    title="User ID",
    description="an encoded user id to restrict query to, must be own id if not admin user",
)

ViewQueryParam: JobIndexViewEnum = Query(
    default="collection",
    title="View",
    description="Determines columns to return. Defaults to 'collection'.",
)


ToolIdQueryParam: Optional[str] = Query(
    default=None,
    title="Tool ID(s)",
    description="Limit listing of jobs to those that match one of the included tool_ids. If none, all are returned",
)


ToolIdLikeQueryParam: Optional[str] = Query(
    default=None,
    title="Tool ID Pattern(s)",
    description="Limit listing of jobs to those that match one of the included tool ID sql-like patterns. If none, all are returned",
)

DateRangeMinQueryParam: Optional[str] = Query(
    default=None,
    title="Date Range Minimum",
    description="Limit listing of jobs to those that are updated after specified date (e.g. '2014-01-01')",
)

DateRangeMaxQueryParam: Optional[str] = Query(
    default=None,
    title="Date Range Maximum",
    description="Limit listing of jobs to those that are updated before specified date (e.g. '2014-01-01')",
)

HistoryIdQueryParam: Optional[str] = Query(
    default=None,
    title="History ID",
    description="Limit listing of jobs to those that match the history_id. If none, jobs from any history may be returned.",
)

WorkflowIdQueryParam: Optional[str] = Query(
    default=None,
    title="Workflow ID",
    description="Limit listing of jobs to those that match the specified workflow ID. If none, jobs from any workflow (or from no workflows) may be returned.",
)

InvocationIdQueryParam: Optional[str] = Query(
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


@router.cbv
class FastAPIJobs:
    job_manager: JobManager = depends(JobManager)
    job_search: JobSearch = depends(JobSearch)
    hda_manager: hdas.HDAManager = depends(hdas.HDAManager)

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
        id = trans.app.security.decode_id(id)
        job = self.job_manager.get_accessible_job(trans, id)
        return view_show_job(trans, job, bool(full))

    @router.get("/api/jobs")
    def index(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        state: Optional[str] = StateQueryParam,
        user_details: bool = UserDetailsQueryParam,
        user_id: Optional[str] = UserIdQueryParam,
        view: JobIndexViewEnum = ViewQueryParam,
        tool_id: Optional[str] = ToolIdQueryParam,
        tool_id_like: Optional[str] = ToolIdLikeQueryParam,
        date_range_min: Optional[str] = DateRangeMinQueryParam,
        date_range_max: Optional[str] = DateRangeMaxQueryParam,
        history_id: Optional[str] = HistoryIdQueryParam,
        workflow_id: Optional[str] = WorkflowIdQueryParam,
        invocation_id: Optional[str] = InvocationIdQueryParam,
        order_by: JobIndexSortByEnum = SortByQueryParam,
        limit: int = LimitQueryParam,
        offset: int = OffsetQueryParam,
    ) -> List[Dict[str, Any]]:
        security = trans.security

        def optional_list(input: Optional[str]) -> Optional[List[str]]:
            if input is None:
                return None
            else:
                return listify(input)

        states = optional_list(state)
        tool_ids = optional_list(tool_id)
        tool_id_likes = optional_list(tool_id_like)
        is_admin = trans.user_is_admin
        if view == JobIndexViewEnum.admin_job_list and not is_admin:
            raise exceptions.AdminRequiredException("Only admins can use the admin_job_list view")
        if user_id:
            decoded_user_id = security.decode_id(user_id)
        else:
            decoded_user_id = None

        if is_admin:
            if decoded_user_id is not None:
                query = trans.sa_session.query(model.Job).filter(model.Job.user_id == decoded_user_id)
            else:
                query = trans.sa_session.query(model.Job)
        else:
            if decoded_user_id is not None and decoded_user_id != trans.user.id:
                raise exceptions.AdminRequiredException("Only admins can index the jobs of others")
            query = trans.sa_session.query(model.Job).filter(model.Job.user_id == trans.user.id)

        def build_and_apply_filters(query, objects, filter_func):
            if objects is not None:
                if isinstance(objects, str):
                    query = query.filter(filter_func(objects))
                elif isinstance(objects, list):
                    t = []
                    for obj in objects:
                        t.append(filter_func(obj))
                    query = query.filter(or_(*t))
            return query

        query = build_and_apply_filters(query, states, lambda s: model.Job.state == s)
        query = build_and_apply_filters(query, tool_ids, lambda t: model.Job.tool_id == t)
        query = build_and_apply_filters(query, tool_id_likes, lambda t: model.Job.tool_id.like(t))
        query = build_and_apply_filters(query, date_range_min, lambda dmin: model.Job.update_time >= dmin)
        query = build_and_apply_filters(query, date_range_max, lambda dmax: model.Job.update_time <= dmax)

        if history_id is not None:
            decoded_history_id = security.decode_id(history_id)
            query = query.filter(model.Job.history_id == decoded_history_id)
        if workflow_id or invocation_id:
            if workflow_id is not None:
                decoded_workflow_id = security.decode_id(workflow_id)
                wfi_step = (
                    trans.sa_session.query(model.WorkflowInvocationStep)
                    .join(model.WorkflowInvocation)
                    .join(model.Workflow)
                    .filter(
                        model.Workflow.stored_workflow_id == decoded_workflow_id,
                    )
                    .subquery()
                )
            elif invocation_id is not None:
                decoded_invocation_id = security.decode_id(invocation_id)
                wfi_step = (
                    trans.sa_session.query(model.WorkflowInvocationStep)
                    .filter(model.WorkflowInvocationStep.workflow_invocation_id == decoded_invocation_id)
                    .subquery()
                )
            query1 = query.join(wfi_step)
            query2 = query.join(model.ImplicitCollectionJobsJobAssociation).join(
                wfi_step,
                model.ImplicitCollectionJobsJobAssociation.implicit_collection_jobs_id
                == wfi_step.c.implicit_collection_jobs_id,
            )
            query = query1.union(query2)

        if order_by == JobIndexSortByEnum.create_time:
            order_by = model.Job.create_time.desc()
        else:
            order_by = model.Job.update_time.desc()
        query = query.order_by(order_by)

        query = query.offset(offset)
        query = query.limit(limit)

        out = []
        for job in query.yield_per(model.YIELD_PER_ROWS):
            job_dict = job.to_dict(view, system_details=is_admin)
            j = security.encode_all_ids(job_dict, True)
            if view == JobIndexViewEnum.admin_job_list:
                j["decoded_job_id"] = job.id
            if user_details:
                j["user_email"] = job.get_user_email()
            out.append(j)

        return out


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
