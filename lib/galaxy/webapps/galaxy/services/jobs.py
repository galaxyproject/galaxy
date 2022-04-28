from enum import Enum
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from sqlalchemy import or_

from galaxy import (
    exceptions,
    model,
)
from galaxy.managers import hdas
from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.jobs import (
    JobManager,
    JobSearch,
    view_show_job,
)
from galaxy.model.index_filter_util import (
    raw_text_column_filter,
    text_column_filter,
)
from galaxy.schema.fields import EncodedDatabaseIdField
from galaxy.schema.schema import Model
from galaxy.util.search import (
    FilteredTerm,
    parse_filters_structured,
    RawTextTerm,
)


class JobIndexViewEnum(str, Enum):
    collection = "collection"
    admin_job_list = "admin_job_list"


class JobIndexSortByEnum(str, Enum):
    create_time = "create_time"
    update_time = "update_time"


class JobIndexPayload(Model):
    states: Optional[List[str]] = None
    user_details: bool = False
    user_id: Optional[str] = None
    view: JobIndexViewEnum = JobIndexViewEnum.collection
    tool_ids: Optional[List[str]] = None
    tool_ids_like: Optional[List[str]] = None
    date_range_min: Optional[str] = None
    date_range_max: Optional[str] = None
    history_id: Optional[str] = None
    workflow_id: Optional[str] = None
    invocation_id: Optional[str] = None
    order_by: JobIndexSortByEnum = JobIndexSortByEnum.update_time
    search: Optional[str] = None
    limit: int = 500
    offset: int = 0


class JobsService:
    job_manager: JobManager
    job_search: JobSearch
    hda_manager: hdas.HDAManager

    def __init__(
        self,
        job_manager: JobManager,
        job_search: JobSearch,
        hda_manager: hdas.HDAManager,
    ):
        self.job_manager = job_manager
        self.job_search = job_search
        self.hda_manager = hda_manager

    def show(
        self,
        trans: ProvidesUserContext,
        id: EncodedDatabaseIdField,
        full: bool = False,
    ) -> Dict[str, Any]:
        id = trans.app.security.decode_id(id)
        job = self.job_manager.get_accessible_job(trans, id)
        return view_show_job(trans, job, bool(full))

    def index(
        self,
        trans: ProvidesUserContext,
        payload: JobIndexPayload,
    ):
        security = trans.security
        is_admin = trans.user_is_admin
        user_details = payload.user_details or payload.view == JobIndexViewEnum.admin_job_list
        if payload.view == JobIndexViewEnum.admin_job_list and not is_admin:
            raise exceptions.AdminRequiredException("Only admins can use the admin_job_list view")
        user_id = payload.user_id
        if user_id:
            decoded_user_id = security.decode_id(user_id)
        else:
            decoded_user_id = None

        if is_admin:
            if decoded_user_id is not None:
                query = trans.sa_session.query(model.Job).filter(model.Job.user_id == decoded_user_id)
            else:
                query = trans.sa_session.query(model.Job)
            if user_details:
                query = query.outerjoin(model.Job.user)

        else:
            if user_details:
                raise exceptions.AdminRequiredException("Only admins can index the jobs with user details enabled")
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

        query = build_and_apply_filters(query, payload.states, lambda s: model.Job.state == s)
        query = build_and_apply_filters(query, payload.tool_ids, lambda t: model.Job.tool_id == t)
        query = build_and_apply_filters(query, payload.tool_ids_like, lambda t: model.Job.tool_id.like(t))
        query = build_and_apply_filters(query, payload.date_range_min, lambda dmin: model.Job.update_time >= dmin)
        query = build_and_apply_filters(query, payload.date_range_max, lambda dmax: model.Job.update_time <= dmax)

        history_id = payload.history_id
        workflow_id = payload.workflow_id
        invocation_id = payload.invocation_id
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

        search = payload.search
        if search:
            search_filters = {
                "tool": "tool",
                "t": "tool",
            }
            if user_details:
                search_filters.update(
                    {
                        "user": "user",
                        "u": "user",
                    }
                )

            if is_admin:
                search_filters.update(
                    {
                        "runner": "runner",
                        "r": "runner",
                        "handler": "handler",
                        "h": "handler",
                    }
                )
            parsed_search = parse_filters_structured(search, search_filters)
            for term in parsed_search.terms:
                if isinstance(term, FilteredTerm):
                    key = term.filter
                    if key == "user":
                        query = query.filter(text_column_filter(model.User.email, term))
                    elif key == "tool":
                        query = query.filter(text_column_filter(model.Job.tool_id, term))
                    elif key == "handler":
                        query = query.filter(text_column_filter(model.Job.handler, term))
                    elif key == "runner":
                        query = query.filter(text_column_filter(model.Job.job_runner_name, term))
                elif isinstance(term, RawTextTerm):
                    columns = [model.Job.tool_id]
                    if user_details:
                        columns.append(model.User.email)
                    if is_admin:
                        columns.append(model.Job.handler)
                        columns.append(model.Job.job_runner_name)
                    query = query.filter(raw_text_column_filter(columns, term))

        if payload.order_by == JobIndexSortByEnum.create_time:
            order_by = model.Job.create_time.desc()
        else:
            order_by = model.Job.update_time.desc()
        query = query.order_by(order_by)

        query = query.offset(payload.offset)
        query = query.limit(payload.limit)
        out = []
        view = payload.view
        for job in query.yield_per(model.YIELD_PER_ROWS):
            job_dict = job.to_dict(view, system_details=is_admin)
            j = security.encode_all_ids(job_dict, True)
            if view == JobIndexViewEnum.admin_job_list:
                j["decoded_job_id"] = job.id
            if user_details:
                j["user_email"] = job.get_user_email()
            out.append(j)

        return out
