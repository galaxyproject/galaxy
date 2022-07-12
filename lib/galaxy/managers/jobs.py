import json
import logging
import typing
from datetime import (
    date,
    datetime,
)

from boltons.iterutils import remap
from pydantic import (
    BaseModel,
    Field,
)
from sqlalchemy import (
    and_,
    false,
    func,
    or_,
)
from sqlalchemy.orm import aliased
from sqlalchemy.sql import select

from galaxy import model
from galaxy.exceptions import (
    AdminRequiredException,
    ItemAccessibilityException,
    ObjectNotFound,
    RequestParameterInvalidException,
)
from galaxy.job_metrics import (
    RawMetric,
    Safety,
)
from galaxy.managers.collections import DatasetCollectionManager
from galaxy.managers.datasets import DatasetManager
from galaxy.managers.hdas import HDAManager
from galaxy.managers.lddas import LDDAManager
from galaxy.model.index_filter_util import (
    raw_text_column_filter,
    text_column_filter,
)
from galaxy.model.scoped_session import galaxy_scoped_session
from galaxy.schema.schema import (
    JobIndexQueryPayload,
    JobIndexSortByEnum,
)
from galaxy.security.idencoding import IdEncodingHelper
from galaxy.structured_app import StructuredApp
from galaxy.util import (
    defaultdict,
    ExecutionTimer,
    listify,
)
from galaxy.util.search import (
    FilteredTerm,
    parse_filters_structured,
    RawTextTerm,
)

log = logging.getLogger(__name__)


class JobLock(BaseModel):
    active: bool = Field(title="Job lock status", description="If active, jobs will not dispatch")


def get_path_key(path_tuple):
    path_key = ""
    tuple_elements = len(path_tuple)
    for i, p in enumerate(path_tuple):
        if isinstance(p, int):
            sep = "_"
        else:
            sep = "|"
        if i == (tuple_elements - 2) and p == "values":
            # dataset inputs are always wrapped in lists. To avoid 'rep_factorName_0|rep_factorLevel_2|countsFile|values_0',
            # we remove the last 2 items of the path tuple (values and list index)
            return path_key
        if path_key:
            path_key = f"{path_key}{sep}{p}"
        else:
            path_key = p
    return path_key


class JobManager:
    def __init__(self, app: StructuredApp):
        self.app = app
        self.dataset_manager = DatasetManager(app)

    def index_query(self, trans, payload: JobIndexQueryPayload):
        is_admin = trans.user_is_admin
        user_details = payload.user_details

        decoded_user_id = payload.user_id

        if is_admin:
            if decoded_user_id is not None:
                query = trans.sa_session.query(model.Job).filter(model.Job.user_id == decoded_user_id)
            else:
                query = trans.sa_session.query(model.Job)
            if user_details:
                query = query.outerjoin(model.Job.user)

        else:
            if user_details:
                raise AdminRequiredException("Only admins can index the jobs with user details enabled")
            if decoded_user_id is not None and decoded_user_id != trans.user.id:
                raise AdminRequiredException("Only admins can index the jobs of others")
            query = trans.sa_session.query(model.Job).filter(model.Job.user_id == trans.user.id)

        def build_and_apply_filters(query, objects, filter_func):
            if objects is not None:
                if isinstance(objects, (str, date, datetime)):
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
            query = query.filter(model.Job.history_id == history_id)
        if workflow_id or invocation_id:
            if workflow_id is not None:
                wfi_step = (
                    trans.sa_session.query(model.WorkflowInvocationStep)
                    .join(model.WorkflowInvocation)
                    .join(model.Workflow)
                    .filter(
                        model.Workflow.stored_workflow_id == workflow_id,
                    )
                    .subquery()
                )
            elif invocation_id is not None:
                wfi_step = (
                    trans.sa_session.query(model.WorkflowInvocationStep)
                    .filter(model.WorkflowInvocationStep.workflow_invocation_id == invocation_id)
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
        return query

    def job_lock(self) -> JobLock:
        return JobLock(active=self.app.job_manager.job_lock)

    def update_job_lock(self, job_lock: JobLock):
        self.app.queue_worker.send_control_task(
            "admin_job_lock", kwargs={"job_lock": job_lock.active}, get_response=True
        )
        return self.job_lock()

    def get_accessible_job(self, trans, decoded_job_id):
        job = trans.sa_session.query(trans.app.model.Job).filter(trans.app.model.Job.id == decoded_job_id).first()
        if job is None:
            raise ObjectNotFound()
        belongs_to_user = (
            (job.user_id == trans.user.id)
            if job.user_id and trans.user
            else (job.session_id == trans.get_galaxy_session().id)
        )
        if not trans.user_is_admin and not belongs_to_user:
            # Check access granted via output datasets.
            if not job.output_datasets:
                raise ItemAccessibilityException("Job has no output datasets.")
            for data_assoc in job.output_datasets:
                if not self.dataset_manager.is_accessible(data_assoc.dataset.dataset, trans.user):
                    raise ItemAccessibilityException("You are not allowed to rerun this job.")
        trans.sa_session.refresh(job)
        return job

    def stop(self, job, message=None):
        if not job.finished:
            job.mark_deleted(self.app.config.track_jobs_in_database)
            self.app.model.session.flush()
            self.app.job_manager.stop(job, message=message)
            return True
        else:
            return False


class JobSearch:
    """Search for jobs using tool inputs or other jobs"""

    def __init__(
        self,
        sa_session: galaxy_scoped_session,
        hda_manager: HDAManager,
        dataset_collection_manager: DatasetCollectionManager,
        ldda_manager: LDDAManager,
        id_encoding_helper: IdEncodingHelper,
    ):
        self.sa_session = sa_session
        self.hda_manager = hda_manager
        self.dataset_collection_manager = dataset_collection_manager
        self.ldda_manager = ldda_manager
        self.decode_id = id_encoding_helper.decode_id

    def by_tool_input(self, trans, tool_id, tool_version, param=None, param_dump=None, job_state="ok"):
        """Search for jobs producing same results using the 'inputs' part of a tool POST."""
        user = trans.user
        input_data = defaultdict(list)

        def populate_input_data_input_id(path, key, value):
            """Traverses expanded incoming using remap and collects input_ids and input_data."""
            if key == "id":
                path_key = get_path_key(path[:-2])
                current_case = param_dump
                for p in path:
                    current_case = current_case[p]
                src = current_case["src"]
                current_case = param
                for i, p in enumerate(path):
                    if p == "values" and i == len(path) - 2:
                        continue
                    if isinstance(current_case, (list, dict)):
                        current_case = current_case[p]
                identifier = getattr(current_case, "element_identifier", None)
                input_data[path_key].append(
                    {
                        "src": src,
                        "id": value,
                        "identifier": identifier,
                    }
                )
                return key, "__id_wildcard__"
            return key, value

        wildcard_param_dump = remap(param_dump, visit=populate_input_data_input_id)
        return self.__search(
            tool_id=tool_id,
            tool_version=tool_version,
            user=user,
            input_data=input_data,
            job_state=job_state,
            param_dump=param_dump,
            wildcard_param_dump=wildcard_param_dump,
        )

    def __search(
        self, tool_id, tool_version, user, input_data, job_state=None, param_dump=None, wildcard_param_dump=None
    ):
        search_timer = ExecutionTimer()

        def replace_dataset_ids(path, key, value):
            """Exchanges dataset_ids (HDA, LDA, HDCA, not Dataset) in param_dump with dataset ids used in job."""
            if key == "id":
                current_case = param_dump
                for p in path:
                    current_case = current_case[p]
                src = current_case["src"]
                value = job_input_ids[src][value]
                return key, value
            return key, value

        job_conditions = [
            and_(
                model.Job.tool_id == tool_id,
                model.Job.user == user,
                model.Job.copied_from_job_id.is_(None),  # Always pick original job
            )
        ]

        if tool_version:
            job_conditions.append(model.Job.tool_version == str(tool_version))

        if job_state is None:
            job_conditions.append(
                model.Job.state.in_(
                    [
                        model.Job.states.NEW,
                        model.Job.states.QUEUED,
                        model.Job.states.WAITING,
                        model.Job.states.RUNNING,
                        model.Job.states.OK,
                    ]
                )
            )
        else:
            if isinstance(job_state, str):
                job_conditions.append(model.Job.state == job_state)
            elif isinstance(job_state, list):
                o = []
                for s in job_state:
                    o.append(model.Job.state == s)
                job_conditions.append(or_(*o))

        for k, v in wildcard_param_dump.items():
            wildcard_value = None
            if v == {"__class__": "RuntimeValue"}:
                # TODO: verify this is always None. e.g. run with runtime input input
                v = None
            elif k.endswith("|__identifier__"):
                # We've taken care of this while constructing the conditions based on ``input_data`` above
                continue
            elif k == "chromInfo" and "?.len" in v:
                continue
                wildcard_value = '"%?.len"'
            if not wildcard_value:
                value_dump = json.dumps(v, sort_keys=True)
                wildcard_value = value_dump.replace('"id": "__id_wildcard__"', '"id": %')
            a = aliased(model.JobParameter)
            if value_dump == wildcard_value:
                job_conditions.append(
                    and_(
                        model.Job.id == a.job_id,
                        a.name == k,
                        a.value == value_dump,
                    )
                )
            else:
                job_conditions.append(and_(model.Job.id == a.job_id, a.name == k, a.value.like(wildcard_value)))

        job_conditions.append(
            and_(
                model.Job.any_output_dataset_collection_instances_deleted == false(),
                model.Job.any_output_dataset_deleted == false(),
            )
        )

        subq = self.sa_session.query(model.Job.id).filter(*job_conditions).subquery()
        data_conditions = []

        # We now build the query filters that relate to the input datasets
        # that this job uses. We keep track of the requested dataset id in `requested_ids`,
        # the type (hda, hdca or lda) in `data_types`
        # and the ids that have been used in the job that has already been run in `used_ids`.
        requested_ids = []
        data_types = []
        used_ids = []
        for k, input_list in input_data.items():
            # k will be matched against the JobParameter.name column. This can be prefixed depending on whethter
            # the input is in a repeat, or not (section and conditional)
            k = {k, k.split("|")[-1]}
            for type_values in input_list:
                t = type_values["src"]
                v = type_values["id"]
                requested_ids.append(v)
                data_types.append(t)
                identifier = type_values["identifier"]
                if t == "hda":
                    a = aliased(model.JobToInputDatasetAssociation)
                    b = aliased(model.HistoryDatasetAssociation)
                    c = aliased(model.HistoryDatasetAssociation)
                    d = aliased(model.JobParameter)
                    e = aliased(model.HistoryDatasetAssociationHistory)
                    stmt = select([model.HistoryDatasetAssociation.id]).where(
                        model.HistoryDatasetAssociation.id == e.history_dataset_association_id
                    )
                    name_condition = []
                    if identifier:
                        data_conditions.append(
                            and_(
                                model.Job.id == d.job_id,
                                d.name.in_({f"{_}|__identifier__" for _ in k}),
                                d.value == json.dumps(identifier),
                            )
                        )
                    else:
                        stmt = stmt.where(e.name == c.name)
                        name_condition.append(b.name == c.name)
                    stmt = (
                        stmt.where(
                            e.extension == c.extension,
                        )
                        .where(
                            a.dataset_version == e.version,
                        )
                        .where(
                            e._metadata == c._metadata,
                        )
                    )
                    data_conditions.append(
                        and_(
                            a.name.in_(k),
                            a.dataset_id == b.id,  # b is the HDA used for the job
                            c.dataset_id == b.dataset_id,
                            c.id == v,  # c is the requested job input HDA
                            # We need to make sure that the job we are looking for has been run with identical inputs.
                            # Here we deal with 3 requirements:
                            #  - the jobs' input dataset (=b) version is 0, meaning the job's input dataset is not yet ready
                            #  - b's update_time is older than the job create time, meaning no changes occurred
                            #  - the job has a dataset_version recorded, and that versions' metadata matches c's metadata.
                            or_(
                                and_(
                                    or_(a.dataset_version.in_([0, b.version]), b.update_time < model.Job.create_time),
                                    b.extension == c.extension,
                                    b.metadata == c.metadata,
                                    *name_condition,
                                ),
                                b.id.in_(stmt),
                            ),
                            or_(b.deleted == false(), c.deleted == false()),
                        )
                    )

                    used_ids.append(a.dataset_id)
                elif t == "ldda":
                    a = aliased(model.JobToInputLibraryDatasetAssociation)
                    data_conditions.append(and_(model.Job.id == a.job_id, a.name.in_(k), a.ldda_id == v))
                    used_ids.append(a.ldda_id)
                elif t == "hdca":
                    a = aliased(model.JobToInputDatasetCollectionAssociation)
                    b = aliased(model.HistoryDatasetCollectionAssociation)
                    c = aliased(model.HistoryDatasetCollectionAssociation)
                    data_conditions.append(
                        and_(
                            model.Job.id == a.job_id,
                            a.name.in_(k),
                            b.id == a.dataset_collection_id,
                            c.id == v,
                            b.name == c.name,
                            or_(
                                and_(b.deleted == false(), b.id == v),
                                and_(
                                    or_(
                                        c.copied_from_history_dataset_collection_association_id == b.id,
                                        b.copied_from_history_dataset_collection_association_id == c.id,
                                    ),
                                    c.deleted == false(),
                                ),
                            ),
                        )
                    )
                    used_ids.append(a.dataset_collection_id)
                elif t == "dce":
                    a = aliased(model.JobToInputDatasetCollectionElementAssociation)
                    b = aliased(model.DatasetCollectionElement)
                    c = aliased(model.DatasetCollectionElement)
                    data_conditions.append(
                        and_(
                            model.Job.id == a.job_id,
                            a.name.in_(k),
                            a.dataset_collection_element_id == b.id,
                            b.element_identifier == c.element_identifier,
                            c.child_collection_id == b.child_collection_id,
                            c.id == v,
                        )
                    )
                    used_ids.append(a.dataset_collection_element_id)
                else:
                    return []

        query = (
            self.sa_session.query(model.Job.id, *used_ids)
            .join(subq, model.Job.id == subq.c.id)
            .filter(*data_conditions)
            .group_by(model.Job.id, *used_ids)
            .order_by(model.Job.id.desc())
        )
        for job in query:
            # We found a job that is equal in terms of tool_id, user, state and input datasets,
            # but to be able to verify that the parameters match we need to modify all instances of
            # dataset_ids (HDA, LDDA, HDCA) in the incoming param_dump to point to those used by the
            # possibly equivalent job, which may have been run on copies of the original input data.
            job_input_ids = {}
            if len(job) > 1:
                # We do have datasets to check
                job_id, current_jobs_data_ids = job[0], job[1:]
                job_parameter_conditions = [model.Job.id == job_id]
                for src, requested_id, used_id in zip(data_types, requested_ids, current_jobs_data_ids):
                    if src not in job_input_ids:
                        job_input_ids[src] = {requested_id: used_id}
                    else:
                        job_input_ids[src][requested_id] = used_id
                new_param_dump = remap(param_dump, visit=replace_dataset_ids)
                # new_param_dump has its dataset ids remapped to those used by the job.
                # We now ask if the remapped job parameters match the current job.
                for k, v in new_param_dump.items():
                    if v == {"__class__": "RuntimeValue"}:
                        # TODO: verify this is always None. e.g. run with runtime input input
                        v = None
                    elif k.endswith("|__identifier__"):
                        # We've taken care of this while constructing the conditions based on ``input_data`` above
                        continue
                    elif k == "chromInfo" and "?.len" in v:
                        continue
                        wildcard_value = '"%?.len"'
                    if not wildcard_value:
                        wildcard_value = json.dumps(v, sort_keys=True).replace('"id": "__id_wildcard__"', '"id": %')
                    a = aliased(model.JobParameter)
                    job_parameter_conditions.append(
                        and_(model.Job.id == a.job_id, a.name == k, a.value == json.dumps(v, sort_keys=True))
                    )
            else:
                job_parameter_conditions = [model.Job.id == job]
            query = self.sa_session.query(model.Job).filter(*job_parameter_conditions)
            job = query.first()
            if job is None:
                continue
            n_parameters = 0
            # Verify that equivalent jobs had the same number of job parameters
            # We skip chrominfo, dbkey, __workflow_invocation_uuid__ and identifer
            # parameter as these are not passed along when expanding tool parameters
            # and they can differ without affecting the resulting dataset.
            for parameter in job.parameters:
                if parameter.name.startswith("__"):
                    continue
                if parameter.name in {"chromInfo", "dbkey"} or parameter.name.endswith("|__identifier__"):
                    continue
                n_parameters += 1
            if not n_parameters == sum(
                1
                for k in param_dump
                if not k.startswith("__") and not k.endswith("|__identifier__") and k not in {"chromInfo", "dbkey"}
            ):
                continue
            log.info("Found equivalent job %s", search_timer)
            return job
        log.info("No equivalent jobs found %s", search_timer)
        return None


def view_show_job(trans, job, full: bool) -> typing.Dict:
    is_admin = trans.user_is_admin
    job_dict = trans.app.security.encode_all_ids(job.to_dict("element", system_details=is_admin), True)
    if trans.app.config.expose_dataset_path and "command_line" not in job_dict:
        job_dict["command_line"] = job.command_line
    if full:
        job_dict.update(
            dict(
                tool_stdout=job.tool_stdout,
                tool_stderr=job.tool_stderr,
                job_stdout=job.job_stdout,
                job_stderr=job.job_stderr,
                stderr=job.stderr,
                stdout=job.stdout,
                job_messages=job.job_messages,
                dependencies=job.dependencies,
            )
        )

        if is_admin:
            job_dict["user_email"] = job.get_user_email()
            job_dict["job_metrics"] = summarize_job_metrics(trans, job)
    return job_dict


def invocation_job_source_iter(sa_session, invocation_id):
    # TODO: Handle subworkflows.
    join = model.WorkflowInvocationStep.table.join(model.WorkflowInvocation)
    statement = (
        select(
            [
                model.WorkflowInvocationStep.job_id,
                model.WorkflowInvocationStep.implicit_collection_jobs_id,
                model.WorkflowInvocationStep.state,
            ]
        )
        .select_from(join)
        .where(model.WorkflowInvocation.id == invocation_id)
    )
    for row in sa_session.execute(statement):
        if row[0]:
            yield ("Job", row[0], row[2])
        if row[1]:
            yield ("ImplicitCollectionJobs", row[1], row[2])


def fetch_job_states(sa_session, job_source_ids, job_source_types):
    assert len(job_source_ids) == len(job_source_types)
    job_ids = set()
    implicit_collection_job_ids = set()
    workflow_invocations_job_sources = {}
    workflow_invocation_states = (
        {}
    )  # should be set before we walk step states to be conservative on whether things are done expanding yet

    for job_source_id, job_source_type in zip(job_source_ids, job_source_types):
        if job_source_type == "Job":
            job_ids.add(job_source_id)
        elif job_source_type == "ImplicitCollectionJobs":
            implicit_collection_job_ids.add(job_source_id)
        elif job_source_type == "WorkflowInvocation":
            invocation_state = sa_session.query(model.WorkflowInvocation).get(job_source_id).state
            workflow_invocation_states[job_source_id] = invocation_state
            workflow_invocation_job_sources = []
            for (
                invocation_step_source_type,
                invocation_step_source_id,
                invocation_step_state,
            ) in invocation_job_source_iter(sa_session, job_source_id):
                workflow_invocation_job_sources.append(
                    (invocation_step_source_type, invocation_step_source_id, invocation_step_state)
                )
                if invocation_step_source_type == "Job":
                    job_ids.add(invocation_step_source_id)
                elif invocation_step_source_type == "ImplicitCollectionJobs":
                    implicit_collection_job_ids.add(invocation_step_source_id)
            workflow_invocations_job_sources[job_source_id] = workflow_invocation_job_sources
        else:
            raise RequestParameterInvalidException(f"Invalid job source type {job_source_type} found.")

    job_summaries = {}
    implicit_collection_jobs_summaries = {}

    for job_id in job_ids:
        job_summaries[job_id] = summarize_jobs_to_dict(sa_session, sa_session.query(model.Job).get(job_id))
    for implicit_collection_jobs_id in implicit_collection_job_ids:
        implicit_collection_jobs_summaries[implicit_collection_jobs_id] = summarize_jobs_to_dict(
            sa_session, sa_session.query(model.ImplicitCollectionJobs).get(implicit_collection_jobs_id)
        )

    rval = []
    for job_source_id, job_source_type in zip(job_source_ids, job_source_types):
        if job_source_type == "Job":
            rval.append(job_summaries[job_source_id])
        elif job_source_type == "ImplicitCollectionJobs":
            rval.append(implicit_collection_jobs_summaries[job_source_id])
        else:
            invocation_state = workflow_invocation_states[job_source_id]
            invocation_job_summaries = []
            invocation_implicit_collection_job_summaries = []
            invocation_step_states = []
            for (
                invocation_step_source_type,
                invocation_step_source_id,
                invocation_step_state,
            ) in workflow_invocations_job_sources[job_source_id]:
                invocation_step_states.append(invocation_step_state)
                if invocation_step_source_type == "Job":
                    invocation_job_summaries.append(job_summaries[invocation_step_source_id])
                else:
                    invocation_implicit_collection_job_summaries.append(
                        implicit_collection_jobs_summaries[invocation_step_source_id]
                    )
            rval.append(
                summarize_invocation_jobs(
                    job_source_id,
                    invocation_job_summaries,
                    invocation_implicit_collection_job_summaries,
                    invocation_state,
                    invocation_step_states,
                )
            )

    return rval


def summarize_invocation_jobs(
    invocation_id, job_summaries, implicit_collection_job_summaries, invocation_state, invocation_step_states
):
    states = {}
    if invocation_state == "scheduled":
        all_scheduled = True
        for invocation_step_state in invocation_step_states:
            all_scheduled = all_scheduled and invocation_step_state == "scheduled"
        if all_scheduled:
            populated_state = "ok"
        else:
            populated_state = "new"
    elif invocation_state in ["cancelled", "failed"]:
        populated_state = "failed"
    else:
        # call new, ready => new
        populated_state = "new"

    def merge_states(component_states):
        for key, value in component_states.items():
            if key not in states:
                states[key] = value
            else:
                states[key] += value

    for job_summary in job_summaries:
        merge_states(job_summary["states"])
    for implicit_collection_job_summary in implicit_collection_job_summaries:
        # 'new' (un-populated collections might not yet have a states entry)
        if "states" in implicit_collection_job_summary:
            merge_states(implicit_collection_job_summary["states"])
        component_populated_state = implicit_collection_job_summary["populated_state"]
        if component_populated_state == "failed":
            populated_state = "failed"
        elif component_populated_state == "new" and populated_state != "failed":
            populated_state = "new"

    rval = {
        "id": invocation_id,
        "model": "WorkflowInvocation",
        "states": states,
        "populated_state": populated_state,
    }
    return rval


def summarize_jobs_to_dict(sa_session, jobs_source):
    """Produce a summary of jobs for job summary endpoints.

    :type   jobs_source: a Job or ImplicitCollectionJobs or None
    :param  jobs_source: the object to summarize

    :rtype:     dict
    :returns:   dictionary containing job summary information
    """
    rval = None
    if jobs_source is None:
        pass
    elif isinstance(jobs_source, model.Job):
        rval = {
            "populated_state": "ok",
            "states": {jobs_source.state: 1},
            "model": "Job",
            "id": jobs_source.id,
        }
    else:
        populated_state = jobs_source.populated_state
        rval = {
            "id": jobs_source.id,
            "populated_state": populated_state,
            "model": "ImplicitCollectionJobs",
        }
        if populated_state == "ok":
            # produce state summary...
            states = {}
            join = model.ImplicitCollectionJobs.table.join(
                model.ImplicitCollectionJobsJobAssociation.table.join(model.Job)
            )
            statement = (
                select([model.Job.state, func.count("*")])
                .select_from(join)
                .where(model.ImplicitCollectionJobs.id == jobs_source.id)
                .group_by(model.Job.state)
            )
            for row in sa_session.execute(statement):
                states[row[0]] = row[1]
            rval["states"] = states
    return rval


def summarize_job_metrics(trans, job):
    """Produce a dict-ified version of job metrics ready for tabular rendering.

    Precondition: the caller has verified the job is accessible to the user
    represented by the trans parameter.
    """
    safety_level = Safety.SAFE
    if trans.user_is_admin:
        safety_level = Safety.UNSAFE
    elif trans.app.config.expose_potentially_sensitive_job_metrics:
        safety_level = Safety.POTENTIALLY_SENSITVE
    raw_metrics = [
        RawMetric(
            m.metric_name,
            m.metric_value,
            m.plugin,
        )
        for m in job.metrics
    ]
    dictifiable_metrics = trans.app.job_metrics.dictifiable_metrics(raw_metrics, safety_level)
    return [d.dict() for d in dictifiable_metrics]


def summarize_destination_params(trans, job):
    """Produce a dict-ified version of job destination parameters ready for tabular rendering.

    Precondition: the caller has verified the job is accessible to the user
    represented by the trans parameter.
    """

    destination_params = {
        "Runner": job.job_runner_name,
        "Runner Job ID": job.job_runner_external_id,
        "Handler": job.handler,
    }
    job_destination_params = job.destination_params
    if job_destination_params:
        destination_params.update(job_destination_params)
    return destination_params


def summarize_job_parameters(trans, job):
    """Produce a dict-ified version of job parameters ready for tabular rendering.

    Precondition: the caller has verified the job is accessible to the user
    represented by the trans parameter.
    """

    def inputs_recursive(input_params, param_values, depth=1, upgrade_messages=None):
        if upgrade_messages is None:
            upgrade_messages = {}

        rval = []

        for input in input_params.values():
            if input.name in param_values:
                if input.type == "repeat":
                    for i in range(len(param_values[input.name])):
                        rval.extend(inputs_recursive(input.inputs, param_values[input.name][i], depth=depth + 1))
                elif input.type == "section":
                    # Get the value of the current Section parameter
                    rval.append(dict(text=input.name, depth=depth))
                    rval.extend(
                        inputs_recursive(
                            input.inputs,
                            param_values[input.name],
                            depth=depth + 1,
                            upgrade_messages=upgrade_messages.get(input.name),
                        )
                    )
                elif input.type == "conditional":
                    try:
                        current_case = param_values[input.name]["__current_case__"]
                        is_valid = True
                    except Exception:
                        current_case = None
                        is_valid = False
                    if is_valid:
                        rval.append(
                            dict(text=input.test_param.label, depth=depth, value=input.cases[current_case].value)
                        )
                        rval.extend(
                            inputs_recursive(
                                input.cases[current_case].inputs,
                                param_values[input.name],
                                depth=depth + 1,
                                upgrade_messages=upgrade_messages.get(input.name),
                            )
                        )
                    else:
                        rval.append(
                            dict(
                                text=input.name,
                                depth=depth,
                                notes="The previously used value is no longer valid.",
                                error=True,
                            )
                        )
                elif input.type == "upload_dataset":
                    rval.append(
                        dict(
                            text=input.group_title(param_values),
                            depth=depth,
                            value=f"{len(param_values[input.name])} uploaded datasets",
                        )
                    )
                elif input.type == "data":
                    value = []
                    for element in listify(param_values[input.name]):
                        encoded_id = trans.security.encode_id(element.id)
                        if isinstance(element, model.HistoryDatasetAssociation):
                            hda = element
                            value.append({"src": "hda", "id": encoded_id, "hid": hda.hid, "name": hda.name})
                        elif isinstance(element, model.DatasetCollectionElement):
                            value.append({"src": "dce", "id": encoded_id, "name": element.element_identifier})
                        elif isinstance(element, model.HistoryDatasetCollectionAssociation):
                            value.append({"src": "hdca", "id": encoded_id, "hid": element.hid, "name": element.name})
                        else:
                            raise Exception(
                                f"Unhandled data input parameter type encountered {element.__class__.__name__}"
                            )
                    rval.append(dict(text=input.label, depth=depth, value=value))
                elif input.visible:
                    if hasattr(input, "label") and input.label:
                        label = input.label
                    else:
                        # value for label not required, fallback to input name (same as tool panel)
                        label = input.name
                    rval.append(
                        dict(
                            text=label,
                            depth=depth,
                            value=input.value_to_display_text(param_values[input.name]),
                            notes=upgrade_messages.get(input.name, ""),
                        )
                    )
            else:
                # Parameter does not have a stored value.
                # Get parameter label.
                if input.type == "conditional":
                    label = input.test_param.label
                elif input.type == "repeat":
                    label = input.label()
                else:
                    label = input.label or input.name
                rval.append(
                    dict(text=label, depth=depth, notes="not used (parameter was added after this job was run)")
                )

        return rval

    # Load the tool
    app = trans.app
    toolbox = app.toolbox
    tool = toolbox.get_tool(job.tool_id, job.tool_version)

    params_objects = None
    parameters = []
    upgrade_messages = {}
    has_parameter_errors = False

    # Load parameter objects, if a parameter type has changed, it's possible for the value to no longer be valid
    if tool:
        try:
            params_objects = job.get_param_values(app, ignore_errors=False)
        except Exception:
            params_objects = job.get_param_values(app, ignore_errors=True)
            # use different param_objects in the following line, since we want to display original values as much as possible
            upgrade_messages = tool.check_and_update_param_values(
                job.get_param_values(app, ignore_errors=True), trans, update_values=False
            )
            has_parameter_errors = True
        parameters = inputs_recursive(tool.inputs, params_objects, depth=1, upgrade_messages=upgrade_messages)
    else:
        has_parameter_errors = True

    return {
        "parameters": parameters,
        "has_parameter_errors": has_parameter_errors,
        "outputs": summarize_job_outputs(job=job, tool=tool, params=params_objects, security=trans.security),
    }


def get_output_name(tool, output, params):
    try:
        return tool.tool_action.get_output_name(
            output,
            tool=tool,
            params=params,
        )
    except Exception:
        pass


def summarize_job_outputs(job: model.Job, tool, params, security):
    outputs = defaultdict(list)
    output_labels = {}
    possible_outputs = (
        ("hda", "dataset_id", job.output_datasets),
        ("ldda", "ldda_id", job.output_library_datasets),
        ("hdca", "dataset_collection_id", job.output_dataset_collection_instances),
    )
    for src, attribute, output_associations in possible_outputs:
        for output_association in output_associations:
            output_name = output_association.name
            if output_name not in output_labels and tool:
                tool_output = tool.output_collections if src == "hdca" else tool.outputs
                output_labels[output_name] = get_output_name(
                    tool=tool, output=tool_output.get(output_name), params=params
                )
            label = output_labels.get(output_name)
            outputs[output_name].append(
                {
                    "label": label,
                    "value": {"src": src, "id": security.encode_id(getattr(output_association, attribute))},
                }
            )
    return outputs
