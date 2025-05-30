import json
import logging
from datetime import (
    date,
    datetime,
)
from pathlib import Path
from typing import (
    Any,
    cast,
    Dict,
    Iterable,
    List,
    Optional,
    Set,
    Union,
)

import sqlalchemy
from boltons.iterutils import remap
from pydantic import (
    BaseModel,
    Field,
)
from sqlalchemy import (
    and_,
    exists,
    false,
    func,
    null,
    or_,
    true,
)
from sqlalchemy.orm import aliased
from sqlalchemy.sql import select
from typing_extensions import TypedDict

from galaxy import model
from galaxy.exceptions import (
    ConfigDoesNotAllowException,
    ItemAccessibilityException,
    ObjectNotFound,
    RequestParameterInvalidException,
    RequestParameterMissingException,
)
from galaxy.job_metrics import (
    RawMetric,
    Safety,
)
from galaxy.managers.collections import DatasetCollectionManager
from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.datasets import DatasetManager
from galaxy.managers.hdas import HDAManager
from galaxy.managers.lddas import LDDAManager
from galaxy.model import (
    ImplicitCollectionJobs,
    ImplicitCollectionJobsJobAssociation,
    Job,
    JobMetricNumeric,
    JobParameter,
    User,
    Workflow,
    WorkflowInvocation,
    WorkflowInvocationStep,
    WorkflowStep,
    YIELD_PER_ROWS,
)
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
from galaxy.tools._types import (
    ToolStateDumpedToJsonInternalT,
    ToolStateJobInstancePopulatedT,
)
from galaxy.util import (
    defaultdict,
    ExecutionTimer,
    listify,
    string_as_bool_or_none,
)
from galaxy.util.search import (
    FilteredTerm,
    parse_filters_structured,
    RawTextTerm,
)

log = logging.getLogger(__name__)

JobStateT = str
JobStatesT = Union[JobStateT, Iterable[JobStateT]]


STDOUT_LOCATION = "outputs/tool_stdout"
STDERR_LOCATION = "outputs/tool_stderr"


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

    def index_query(self, trans: ProvidesUserContext, payload: JobIndexQueryPayload) -> sqlalchemy.engine.ScalarResult:
        """The caller is responsible for security checks on the resulting job if
        history_id, invocation_id, or implicit_collection_jobs_id is set.
        Otherwise this will only return the user's jobs or all jobs if the requesting
        user is acting as an admin.
        """
        is_admin = trans.user_is_admin
        user_details = payload.user_details
        decoded_user_id = payload.user_id
        history_id = payload.history_id
        workflow_id = payload.workflow_id
        invocation_id = payload.invocation_id
        implicit_collection_jobs_id = payload.implicit_collection_jobs_id
        search = payload.search
        order_by = payload.order_by

        def build_and_apply_filters(stmt, objects, filter_func):
            if objects is not None:
                if isinstance(objects, (str, date, datetime)):
                    stmt = stmt.where(filter_func(objects))
                elif isinstance(objects, list):
                    t = []
                    for obj in objects:
                        t.append(filter_func(obj))
                    stmt = stmt.where(or_(*t))
            return stmt

        def add_workflow_jobs():
            wfi_step = select(WorkflowInvocationStep)
            if workflow_id is not None:
                wfi_step = (
                    wfi_step.join(WorkflowInvocation).join(Workflow).where(Workflow.stored_workflow_id == workflow_id)
                )
            elif invocation_id is not None:
                wfi_step = wfi_step.where(WorkflowInvocationStep.workflow_invocation_id == invocation_id)
            wfi_step_sq = wfi_step.subquery()

            stmt1 = stmt.join(wfi_step_sq)
            stmt2 = stmt.join(ImplicitCollectionJobsJobAssociation).join(
                wfi_step_sq,
                ImplicitCollectionJobsJobAssociation.implicit_collection_jobs_id
                == wfi_step_sq.c.implicit_collection_jobs_id,
            )
            # Ensure the result is models, not tuples
            sq = stmt1.union(stmt2).subquery()
            # SQLite won't recognize Job.foo as a valid column for the ORDER BY clause due to the UNION clause, so we'll use the subquery `columns` collection (`sq.c`).
            # Ref: https://github.com/galaxyproject/galaxy/pull/16852#issuecomment-1804676322
            return select(aliased(Job, sq)), sq.c

        def add_search_criteria(stmt):
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
            assert search
            parsed_search = parse_filters_structured(search, search_filters)
            for term in parsed_search.terms:
                if isinstance(term, FilteredTerm):
                    key = term.filter
                    if key == "user":
                        stmt = stmt.where(text_column_filter(User.email, term))
                    elif key == "tool":
                        stmt = stmt.where(text_column_filter(Job.tool_id, term))
                    elif key == "handler":
                        stmt = stmt.where(text_column_filter(Job.handler, term))
                    elif key == "runner":
                        stmt = stmt.where(text_column_filter(Job.job_runner_name, term))
                elif isinstance(term, RawTextTerm):
                    columns: List = [Job.tool_id]
                    if user_details:
                        columns.append(User.email)
                    if is_admin:
                        columns.append(Job.handler)
                        columns.append(Job.job_runner_name)
                    stmt = stmt.filter(raw_text_column_filter(columns, term))
            return stmt

        stmt = select(Job)

        if is_admin:
            if decoded_user_id is not None:
                stmt = stmt.where(Job.user_id == decoded_user_id)
            if user_details:
                stmt = stmt.outerjoin(Job.user)
        else:
            if history_id is None and invocation_id is None and implicit_collection_jobs_id is None:
                # If we're not filtering on history, invocation or collection we filter the jobs owned by the current user
                if trans.user:
                    stmt = stmt.where(Job.user_id == trans.user.id)
                elif trans.galaxy_session:
                    stmt = stmt.where(Job.session_id == trans.galaxy_session.id)
                else:
                    raise RequestParameterMissingException("A session is required to list jobs for anonymous users")

        stmt = build_and_apply_filters(stmt, payload.states, lambda s: model.Job.state == s)
        stmt = build_and_apply_filters(stmt, payload.tool_ids, lambda t: model.Job.tool_id == t)
        stmt = build_and_apply_filters(stmt, payload.tool_ids_like, lambda t: model.Job.tool_id.like(t))
        stmt = build_and_apply_filters(stmt, payload.date_range_min, lambda dmin: model.Job.update_time >= dmin)
        stmt = build_and_apply_filters(stmt, payload.date_range_max, lambda dmax: model.Job.update_time <= dmax)

        if history_id is not None:
            stmt = stmt.where(Job.history_id == history_id)

        order_by_columns = Job
        if workflow_id or invocation_id:
            stmt, order_by_columns = add_workflow_jobs()
        elif implicit_collection_jobs_id:
            stmt = (
                stmt.join(ImplicitCollectionJobsJobAssociation, ImplicitCollectionJobsJobAssociation.job_id == Job.id)
                .join(
                    ImplicitCollectionJobs,
                    ImplicitCollectionJobs.id == ImplicitCollectionJobsJobAssociation.implicit_collection_jobs_id,
                )
                .where(ImplicitCollectionJobsJobAssociation.implicit_collection_jobs_id == implicit_collection_jobs_id)
            )
        if search:
            stmt = add_search_criteria(stmt)

        if order_by == JobIndexSortByEnum.create_time:
            stmt = stmt.order_by(order_by_columns.create_time.desc())
        else:
            stmt = stmt.order_by(order_by_columns.update_time.desc())

        stmt = stmt.offset(payload.offset)
        stmt = stmt.limit(payload.limit)
        return trans.sa_session.scalars(stmt)

    def job_lock(self) -> JobLock:
        return JobLock(active=self.app.job_manager.job_lock)

    def update_job_lock(self, job_lock: JobLock):
        self.app.queue_worker.send_control_task(
            "admin_job_lock", kwargs={"job_lock": job_lock.active}, get_response=True
        )
        return self.job_lock()

    def get_accessible_job(self, trans: ProvidesUserContext, decoded_job_id) -> Job:
        job = trans.sa_session.get(Job, decoded_job_id)
        if job is None:
            raise ObjectNotFound()
        belongs_to_user = False
        if trans.user:
            belongs_to_user = job.user_id == trans.user.id
        elif trans.galaxy_session:
            belongs_to_user = job.session_id == trans.galaxy_session.id
        if not trans.user_is_admin and not belongs_to_user:
            # Check access granted via output datasets.
            if not job.output_datasets:
                raise ItemAccessibilityException("Job has no output datasets.")
            for data_assoc in job.output_datasets:
                if not self.dataset_manager.is_accessible(data_assoc.dataset.dataset, trans.user):
                    raise ItemAccessibilityException("You are not allowed to rerun this job.")
        trans.sa_session.refresh(job)
        return job

    def get_job_console_output(
        self, trans, job, stdout_position=-1, stdout_length=0, stderr_position=-1, stderr_length=0
    ):
        if job is None:
            raise ObjectNotFound()

        # Check job destination params to see if stdout reporting is enabled
        dest_params = job.destination_params
        if not string_as_bool_or_none(dest_params.get("live_tool_output_reporting", False)):
            raise ConfigDoesNotAllowException()

        # If stdout_length and stdout_position are good values, then load standard out and add it to status
        console_output = {}
        console_output["state"] = job.state
        if job.state == job.states.RUNNING:
            working_directory = trans.app.object_store.get_filename(
                job, base_dir="job_work", dir_only=True, obj_dir=True
            )
            if stdout_length > -1 and stdout_position > -1:
                try:
                    stdout_path = Path(working_directory) / STDOUT_LOCATION
                    stdout_file = open(stdout_path)
                    stdout_file.seek(stdout_position)
                    console_output["stdout"] = stdout_file.read(stdout_length)
                except Exception as e:
                    log.error("Could not read STDOUT: %s", e)
                    console_output["stdout"] = ""
            if stderr_length > -1 and stderr_position > -1:
                try:
                    stderr_path = Path(working_directory) / STDERR_LOCATION
                    stderr_file = open(stderr_path)
                    stderr_file.seek(stderr_position)
                    console_output["stderr"] = stderr_file.read(stderr_length)
                except Exception as e:
                    log.error("Could not read STDERR: %s", e)
                    console_output["stderr"] = ""
        else:
            console_output["stdout"] = job.tool_stdout
            console_output["stderr"] = job.tool_stderr
        return console_output

    def stop(self, job, message=None):
        if not job.finished:
            job.mark_deleted(self.app.config.track_jobs_in_database, message)
            session = self.app.model.session
            session.commit()
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

    def by_tool_input(
        self,
        user: User,
        tool_id: str,
        tool_version: Optional[str],
        param: ToolStateJobInstancePopulatedT,
        param_dump: ToolStateDumpedToJsonInternalT,
        job_state: Optional[JobStatesT] = (Job.states.OK,),
        require_name_match: bool = True,
    ):
        """Search for jobs producing same results using the 'inputs' part of a tool POST."""
        input_data = defaultdict(list)

        def populate_input_data_input_id(path, key, value):
            """Traverses expanded incoming using remap and collects input_ids and input_data."""
            if key == "id":
                path_key = get_path_key(path[:-2])
                current_case = param_dump
                for p in path:
                    current_case = current_case[p]
                src = current_case.get("src")
                if src is None:
                    # just a parameter named id.
                    # TODO: dispatch on tool parameter type instead of values,
                    # maybe with tool state variant
                    return key, value
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
            require_name_match=require_name_match,
        )

    def __search(
        self,
        tool_id: str,
        tool_version: Optional[str],
        user: model.User,
        input_data,
        job_state: Optional[JobStatesT],
        param_dump: ToolStateDumpedToJsonInternalT,
        wildcard_param_dump=None,
        require_name_match: bool = True,
    ):
        search_timer = ExecutionTimer()

        def replace_dataset_ids(path, key, value):
            """Exchanges dataset_ids (HDA, LDA, HDCA, not Dataset) in param_dump with dataset ids used in job."""
            if key == "id":
                current_case = param_dump
                for p in path:
                    current_case = current_case[p]
                src = current_case.get("src")
                if src is None:
                    # just a parameter named id.
                    # same workaround as in populate_input_data_input_id
                    return key, value
                value = job_input_ids[src][value]
                return key, value
            return key, value

        stmt = select(model.Job.id.label("job_id"))

        data_conditions: List = []

        # We now build the stmt filters that relate to the input datasets
        # that this job uses. We keep track of the requested dataset id in `requested_ids`,
        # the type (hda, hdca or lda) in `data_types`
        # and the ids that have been used in the job that has already been run in `used_ids`.
        requested_ids = []
        data_types = []
        used_ids: List = []
        for k, input_list in input_data.items():
            # k will be matched against the JobParameter.name column. This can be prefixed depending on whethter
            # the input is in a repeat, or not (section and conditional)
            for type_values in input_list:
                t = type_values["src"]
                v = type_values["id"]
                requested_ids.append(v)
                data_types.append(t)
                identifier = type_values["identifier"]
                if t == "hda":
                    stmt = self._build_stmt_for_hda(
                        stmt, data_conditions, used_ids, k, v, identifier, require_name_match=require_name_match
                    )
                elif t == "ldda":
                    stmt = self._build_stmt_for_ldda(stmt, data_conditions, used_ids, k, v)
                elif t == "hdca":
                    stmt = self._build_stmt_for_hdca(stmt, data_conditions, used_ids, k, v, user.id)
                elif t == "dce":
                    stmt = self._build_stmt_for_dce(stmt, data_conditions, used_ids, k, v, user.id)
                else:
                    log.error("Unknown input data type %s", t)
                    return None

        stmt = stmt.where(*data_conditions).group_by(model.Job.id, *used_ids)
        stmt = self._filter_jobs(stmt, tool_id, user.id, tool_version, job_state, wildcard_param_dump)
        stmt = self._exclude_jobs_with_deleted_outputs(stmt)

        for job in self.sa_session.execute(stmt):
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
                    elif k == "__when_value__":
                        continue
                    a = aliased(model.JobParameter)
                    job_parameter_conditions.append(
                        and_(
                            model.Job.id == a.job_id,
                            a.name == k,
                            a.value == (None if v is None else json.dumps(v, sort_keys=True)),
                        )
                    )
            else:
                job_parameter_conditions = [model.Job.id == job[0]]
            job = get_job(self.sa_session, *job_parameter_conditions)
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

    def _filter_jobs(
        self, stmt, tool_id: str, user_id: int, tool_version: Optional[str], job_state, wildcard_param_dump
    ):
        """Build subquery that selects a job with correct job parameters."""
        subquery_alias = stmt.subquery("job_ids_subquery")
        outer_select_columns = [subquery_alias.c[col.name] for col in stmt.selected_columns]
        stmt = select(*outer_select_columns).select_from(subquery_alias)
        stmt = (
            stmt.join(model.Job, model.Job.id == subquery_alias.c.job_id)
            .join(model.History, model.Job.history_id == model.History.id)
            .where(
                and_(
                    model.Job.tool_id == tool_id,
                    or_(
                        model.Job.user_id == user_id,
                        model.History.published == true(),
                    ),
                    model.Job.copied_from_job_id.is_(None),  # Always pick original job
                )
            )
        )
        if tool_version:
            stmt = stmt.where(Job.tool_version == str(tool_version))

        if job_state is None:
            job_states: Set[str] = {
                Job.states.NEW,
                Job.states.QUEUED,
                Job.states.WAITING,
                Job.states.RUNNING,
                Job.states.OK,
            }
        else:
            if isinstance(job_state, str):
                job_states = {job_state}
            else:
                job_states = {*job_state}
        if wildcard_param_dump.get("__when_value__") is False:
            job_states = {Job.states.SKIPPED}
        stmt = stmt.where(Job.state.in_(job_states))

        for k, v in wildcard_param_dump.items():
            if v == {"__class__": "RuntimeValue"}:
                # TODO: verify this is always None. e.g. run with runtime input input
                v = None
            elif k.endswith("|__identifier__"):
                # We've taken care of this while constructing the conditions based on ``input_data`` above
                continue
            elif k == "chromInfo" and "?.len" in v:
                continue
            elif k == "__when_value__":
                # TODO: really need to separate this.
                continue
            value_dump = None if v is None else json.dumps(v, sort_keys=True)
            wildcard_value = value_dump.replace('"id": "__id_wildcard__"', '"id": %') if value_dump else None
            a = aliased(JobParameter)
            if value_dump == wildcard_value:
                # No wildcard needed, use exact match
                stmt = stmt.join(a).where(
                    and_(
                        Job.id == a.job_id,
                        a.name == k,
                        a.value == value_dump,
                    )
                )
            else:
                stmt = stmt.join(a).where(
                    and_(
                        Job.id == a.job_id,
                        a.name == k,
                        a.value.like(wildcard_value),
                    )
                )

        return stmt

    def _exclude_jobs_with_deleted_outputs(self, stmt):
        subquery_alias = stmt.subquery("filtered_jobs_subquery")
        outer_select_columns = [subquery_alias.c[col.name] for col in stmt.selected_columns]
        outer_stmt = select(*outer_select_columns).select_from(subquery_alias)
        job_id_from_subquery = subquery_alias.c.job_id
        deleted_collection_exists = exists().where(
            and_(
                model.JobToOutputDatasetCollectionAssociation.job_id == job_id_from_subquery,
                model.JobToOutputDatasetCollectionAssociation.dataset_collection_id
                == model.HistoryDatasetCollectionAssociation.id,
                model.HistoryDatasetCollectionAssociation.deleted == true(),
            )
        )

        # Subquery for deleted output datasets
        deleted_dataset_exists = exists().where(
            and_(
                model.JobToOutputDatasetAssociation.job_id == job_id_from_subquery,
                model.JobToOutputDatasetAssociation.dataset_id == model.HistoryDatasetAssociation.id,
                model.HistoryDatasetAssociation.deleted == true(),
            )
        )

        # Exclude jobs where a deleted collection OR a deleted dataset exists
        outer_stmt = outer_stmt.where(
            and_(
                ~deleted_collection_exists,  # NOT EXISTS deleted collection
                ~deleted_dataset_exists,  # NOT EXISTS deleted dataset
            )
        ).order_by(job_id_from_subquery.desc())
        return outer_stmt

    def _build_stmt_for_hda(self, stmt, data_conditions, used_ids, k, v, identifier, require_name_match=True):
        a = aliased(model.JobToInputDatasetAssociation)
        b = aliased(model.HistoryDatasetAssociation)
        c = aliased(model.HistoryDatasetAssociation)
        d = aliased(model.JobParameter)
        e = aliased(model.HistoryDatasetAssociationHistory)
        labeled_col = a.dataset_id.label(f"{k}_{v}")
        stmt = stmt.add_columns(labeled_col)
        used_ids.append(labeled_col)
        stmt = stmt.join(a, a.job_id == model.Job.id)
        hda_stmt = select(model.HistoryDatasetAssociation.id).where(
            model.HistoryDatasetAssociation.id == e.history_dataset_association_id
        )
        # b is the HDA used for the job
        stmt = stmt.join(b, a.dataset_id == b.id).join(c, c.dataset_id == b.dataset_id)
        name_condition = []
        if identifier:
            stmt = stmt.join(d)
            data_conditions.append(
                and_(
                    d.name == f"{k}|__identifier__",
                    d.value == json.dumps(identifier),
                )
            )
        elif require_name_match:
            hda_stmt = hda_stmt.where(e.name == c.name)
            name_condition.append(b.name == c.name)
        hda_stmt = (
            hda_stmt.where(
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
                a.name == k,
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
                    b.id.in_(hda_stmt),
                ),
                or_(b.deleted == false(), c.deleted == false()),
            )
        )
        return stmt

    def _build_stmt_for_ldda(self, stmt, data_conditions, used_ids, k, v):
        a = aliased(model.JobToInputLibraryDatasetAssociation)
        labeled_col = a.ldda_id.label(f"{k}_{v}")
        stmt = stmt.add_columns(labeled_col)
        stmt = stmt.join(a, a.job_id == model.Job.id)
        data_conditions.append(and_(a.name == k, a.ldda_id == v))
        used_ids.append(labeled_col)
        return stmt

    def _build_stmt_for_hdca(self, stmt, data_conditions, used_ids, k, v, user_id, require_name_match=True):
        # Strategy for efficiently finding equivalent HDCAs:
        # 1. Determine the structural depth of the target HDCA by its collection_type.
        # 2. For the target HDCA (identified by 'v'):
        #    a. Dynamically construct Common Table Expressions (CTEs) to traverse its (potentially nested) structure down to individual datasets.
        #    b. Generate a "path signature string" for each dataset element, uniquely identifying its path within the collection.
        #    c. Aggregate these path strings into a canonical, sorted array (the "reference full signature") using array_agg with explicit ordering.
        # 3. For all candidate HDCAs:
        #    a. Perform a similar dynamic traversal and path signature string generation.
        #    b. Aggregate these into sorted "full signature" arrays for each candidate HDCA.
        # 4. Finally, identify equivalent HDCAs by comparing their full signature array directly against the reference full signature array.
        #
        # This approach is performant because:
        # - It translates the complex problem of structural collection comparison into efficient array equality checks directly within the database.
        # - It leverages the power of SQL CTEs and set-based operations, allowing the database query optimizer to find an efficient execution plan.
        # - Joins required to traverse collection structures are built dynamically based on the actual depth, avoiding unnecessary complexity.
        # - Signatures are computed and compared entirely on the database side, minimizing data transfer to the application.
        #
        # Note: CTEs are uniquely named using 'k' and 'v' to allow this logic to be embedded
        # within larger queries or loops processing multiple target HDCAs. Aliases are used
        # extensively to manage dynamic joins based on collection depth.
        collection_type = self.sa_session.scalar(
            select(model.DatasetCollection.collection_type)
            .select_from(model.HistoryDatasetCollectionAssociation)
            .join(model.DatasetCollection)
            .where(model.HistoryDatasetCollectionAssociation.id == v)
        )
        depth = collection_type.count(":") if collection_type else 0

        a = aliased(model.JobToInputDatasetCollectionAssociation, name=f"job_to_input_dataset_collection_1_{k}_{v}")
        hdca_input = aliased(
            model.HistoryDatasetCollectionAssociation, name=f"history_dataset_collection_association_1_{k}_{v}"
        )

        _hdca_target_cte_ref = aliased(model.HistoryDatasetCollectionAssociation, name="_hdca_target_cte_ref")
        _target_collection_cte_ref = aliased(model.DatasetCollection, name="_target_collection_cte_ref")
        _dce_cte_ref_list = [
            aliased(model.DatasetCollectionElement, name=f"_dce_cte_ref_{i}") for i in range(depth + 1)
        ]
        _hda_cte_ref = aliased(model.HistoryDatasetAssociation, name="_hda_cte_ref")

        # --- NEW CTE: reference_hdca_all_dataset_ids_cte ---
        # This CTE identifies all distinct dataset IDs that are part of the *reference*
        # History Dataset Collection Association (HDCA). This is used for an initial,
        # fast pre-filtering of candidate HDCAs.
        reference_all_dataset_ids_select = (
            select(_hda_cte_ref.dataset_id.label("ref_dataset_id_for_overlap"))
            .select_from(_hdca_target_cte_ref)
            .join(_target_collection_cte_ref, _target_collection_cte_ref.id == _hdca_target_cte_ref.collection_id)
            .join(_dce_cte_ref_list[0], _dce_cte_ref_list[0].dataset_collection_id == _target_collection_cte_ref.id)
        )

        for i in range(1, depth + 1):
            reference_all_dataset_ids_select = reference_all_dataset_ids_select.join(
                _dce_cte_ref_list[i],
                _dce_cte_ref_list[i].dataset_collection_id == _dce_cte_ref_list[i - 1].child_collection_id,
            )

        _leaf_cte_ref = _dce_cte_ref_list[-1]
        reference_all_dataset_ids_select = (
            reference_all_dataset_ids_select.join(_hda_cte_ref, _hda_cte_ref.id == _leaf_cte_ref.hda_id)
            .where(_hdca_target_cte_ref.id == v)
            .distinct()
        )
        reference_all_dataset_ids_cte = reference_all_dataset_ids_select.cte(f"ref_all_ds_ids_{k}_{v}")
        # --- END NEW CTE ---

        # CTE 1: signature_elements_cte (for the reference HDCA)
        # This CTE generates a unique "path signature string" for each dataset element
        # within the reference HDCA. This string identifies the element's position
        # and content within the nested collection structure.
        signature_elements_select = (
            select(
                func.concat_ws(
                    ";",
                    *[_dce_cte_ref_list[i].element_identifier for i in range(depth + 1)],
                    _hda_cte_ref.dataset_id.cast(sqlalchemy.Text),
                ).label("path_signature_string")
            )
            .select_from(_hdca_target_cte_ref)
            .join(_target_collection_cte_ref, _target_collection_cte_ref.id == _hdca_target_cte_ref.collection_id)
            .join(_dce_cte_ref_list[0], _dce_cte_ref_list[0].dataset_collection_id == _target_collection_cte_ref.id)
        )

        for i in range(1, depth + 1):
            signature_elements_select = signature_elements_select.join(
                _dce_cte_ref_list[i],
                _dce_cte_ref_list[i].dataset_collection_id == _dce_cte_ref_list[i - 1].child_collection_id,
            )

        _leaf_cte_ref = _dce_cte_ref_list[-1]
        signature_elements_select = signature_elements_select.join(
            _hda_cte_ref, _hda_cte_ref.id == _leaf_cte_ref.hda_id
        )
        signature_elements_select = signature_elements_select.where(_hdca_target_cte_ref.id == v)
        signature_elements_cte = signature_elements_select.cte(f"signature_elements_{k}_{v}")

        # CTE 2: reference_full_signature_cte
        # This CTE aggregates the path signature strings of the reference HDCA into a
        # canonical, sorted array. This array represents the complete "signature" of the collection.
        reference_full_signature_cte = (
            select(
                func.array_agg(
                    sqlalchemy.text(
                        f"{signature_elements_cte.c.path_signature_string.name} ORDER BY {signature_elements_cte.c.path_signature_string.name}"
                    )
                ).label("signature_array")
            )
            .select_from(signature_elements_cte)
            .cte(f"reference_full_signature_{k}_{v}")
        )

        candidate_hdca = aliased(model.HistoryDatasetCollectionAssociation, name="candidate_hdca")
        candidate_hdca_history = aliased(model.History, name="candidate_hdca_history")
        candidate_root_collection = aliased(model.DatasetCollection, name="candidate_root_collection")
        candidate_dce_list = [
            aliased(model.DatasetCollectionElement, name=f"candidate_dce_{i}") for i in range(depth + 1)
        ]
        candidate_hda = aliased(model.HistoryDatasetAssociation, name="candidate_hda")

        # --- NEW CTE: candidate_hdca_pre_filter_ids_cte (First Pass Candidate Filtering) ---
        # This CTE performs a quick initial filter on candidate HDCAs.
        # It checks for:
        # 1. User permissions (published or owned by the current user).
        # 2. Whether the candidate HDCA contains any dataset IDs that are also present
        #    in the reference HDCA (an overlap check). This is a broad filter to
        #    reduce the number of candidates before more expensive signature generation.
        candidate_hdca_pre_filter_ids_select = (
            select(candidate_hdca.id.label("candidate_hdca_id"))
            .distinct()
            .select_from(candidate_hdca)
            .join(candidate_hdca_history, candidate_hdca_history.id == candidate_hdca.history_id)
            .join(candidate_root_collection, candidate_root_collection.id == candidate_hdca.collection_id)
            .join(candidate_dce_list[0], candidate_dce_list[0].dataset_collection_id == candidate_root_collection.id)
        )

        for i in range(1, depth + 1):
            candidate_hdca_pre_filter_ids_select = candidate_hdca_pre_filter_ids_select.join(
                candidate_dce_list[i],
                candidate_dce_list[i].dataset_collection_id == candidate_dce_list[i - 1].child_collection_id,
            )

        _leaf_candidate_dce_pre = candidate_dce_list[-1]
        candidate_hdca_pre_filter_ids_select = (
            candidate_hdca_pre_filter_ids_select.join(candidate_hda, candidate_hda.id == _leaf_candidate_dce_pre.hda_id)
            .where(or_(candidate_hdca_history.user_id == user_id, candidate_hdca_history.published == true()))
            .where(candidate_hda.dataset_id.in_(select(reference_all_dataset_ids_cte.c.ref_dataset_id_for_overlap)))
        )
        candidate_hdca_pre_filter_ids_cte = candidate_hdca_pre_filter_ids_select.cte(
            f"cand_hdca_pre_filter_ids_{k}_{v}"
        )
        # --- END NEW CTE ---

        # CTE 3: candidate_signature_elements_cte
        # This CTE generates the path signature string for each element of the
        # *pre-filtered candidate* HDCAs.
        candidate_signature_elements_select = (
            select(
                candidate_hdca.id.label("candidate_hdca_id"),
                func.concat_ws(
                    ";",
                    *[candidate_dce_list[i].element_identifier for i in range(depth + 1)],
                    candidate_hda.dataset_id.cast(sqlalchemy.Text),
                ).label("path_signature_string"),
            )
            .select_from(candidate_hdca)
            # Apply the pre-filter here to limit the candidates for full signature generation
            .where(candidate_hdca.id.in_(select(candidate_hdca_pre_filter_ids_cte.c.candidate_hdca_id)))
            .join(candidate_hdca_history, candidate_hdca_history.id == candidate_hdca.history_id)
            .join(candidate_root_collection, candidate_root_collection.id == candidate_hdca.collection_id)
            .join(candidate_dce_list[0], candidate_dce_list[0].dataset_collection_id == candidate_root_collection.id)
            .where(or_(candidate_hdca_history.user_id == user_id, candidate_hdca_history.published == true()))
        )

        for i in range(1, depth + 1):
            candidate_signature_elements_select = candidate_signature_elements_select.join(
                candidate_dce_list[i],
                candidate_dce_list[i].dataset_collection_id == candidate_dce_list[i - 1].child_collection_id,
            )

        _leaf_candidate_dce = candidate_dce_list[-1]
        candidate_signature_elements_select = candidate_signature_elements_select.join(
            candidate_hda, candidate_hda.id == _leaf_candidate_dce.hda_id
        )
        candidate_signature_elements_cte = candidate_signature_elements_select.cte(
            f"candidate_signature_elements_{k}_{v}"
        )

        # CTE 4: candidate_full_signatures_cte
        # This CTE aggregates the path signature strings for the candidate HDCAs into
        # ordered arrays, similar to the reference's full signature.
        candidate_full_signatures_cte = (
            select(
                candidate_signature_elements_cte.c.candidate_hdca_id,
                func.array_agg(
                    sqlalchemy.text(
                        f"{candidate_signature_elements_cte.c.path_signature_string.name} ORDER BY {candidate_signature_elements_cte.c.path_signature_string.name}"
                    )
                ).label("full_signature_array"),
            )
            .select_from(candidate_signature_elements_cte)
            .group_by(candidate_signature_elements_cte.c.candidate_hdca_id)
            .cte(f"candidate_full_signatures_{k}_{v}")
        )

        # CTE 5: equivalent_hdca_ids_cte
        # This final CTE identifies the HDCAs that are truly "equivalent" by
        # comparing their full signature array to the reference HDCA's full signature array.
        equivalent_hdca_ids_cte = (
            select(candidate_full_signatures_cte.c.candidate_hdca_id.label("equivalent_id"))
            .where(
                candidate_full_signatures_cte.c.full_signature_array
                == select(reference_full_signature_cte.c.signature_array).scalar_subquery()
            )
            .cte(f"equivalent_hdca_ids_{k}_{v}")
        )

        # Main query `stmt` construction
        # This section joins the base job statement with the associations and then filters
        # by the HDCAs identified as equivalent in the CTEs.
        labeled_col = a.dataset_collection_id.label(f"{k}_{v}")
        stmt = stmt.add_columns(labeled_col)
        stmt = stmt.join(a, a.job_id == model.Job.id)

        stmt = stmt.join(
            hdca_input,
            and_(
                hdca_input.id == a.dataset_collection_id,
                # Filter the main query to only include HDCAs found in the
                # 'equivalent_hdca_ids_cte'.
                hdca_input.id.in_(select(equivalent_hdca_ids_cte.c.equivalent_id)),
            ),
        )

        used_ids.append(labeled_col)
        data_conditions.append(a.name == k)
        return stmt

    def _build_stmt_for_dce(self, stmt, data_conditions, used_ids, k, v, user_id):
        dce_root_target = self.sa_session.get_one(model.DatasetCollectionElement, v)

        # Determine if the target DCE points to an HDA or a child collection
        if dce_root_target.child_collection_id:
            # This DCE represents a collection, apply the signature comparison approach
            target_collection_id = dce_root_target.child_collection_id
            collection_type = self.sa_session.scalar(
                select(model.DatasetCollection.collection_type).where(
                    model.DatasetCollection.id == target_collection_id
                )
            )
            depth = collection_type.count(":") if collection_type else 0

            # Aliases for the target DCE's collection structure
            _dce_target_root_ref = aliased(model.DatasetCollectionElement, name=f"_dce_target_root_ref_{k}_{v}")
            _dce_target_child_collection_ref = aliased(
                model.DatasetCollection, name=f"_dce_target_child_collection_ref_{k}_{v}"
            )
            # List of aliases for each potential nested level of DatasetCollectionElements
            _dce_target_level_list = [
                aliased(model.DatasetCollectionElement, name=f"_dce_target_level_{k}_{v}_{i}") for i in range(depth + 1)
            ]
            _hda_target_ref = aliased(model.HistoryDatasetAssociation, name=f"_hda_target_ref_{k}_{v}")

            # --- CTE: reference_dce_all_dataset_ids_cte ---
            # This CTE (Common Table Expression) identifies all distinct dataset IDs
            # that are part of the *reference* dataset collection (the one we're searching for).
            # This helps in the initial filtering of candidate collections.
            reference_all_dataset_ids_select = (
                select(_hda_target_ref.dataset_id.label("ref_dataset_id_for_overlap"))
                .select_from(_dce_target_root_ref)
                .join(
                    _dce_target_child_collection_ref,
                    _dce_target_child_collection_ref.id == _dce_target_root_ref.child_collection_id,
                )
                .join(
                    _dce_target_level_list[0],
                    _dce_target_level_list[0].dataset_collection_id == _dce_target_child_collection_ref.id,
                )
            )
            # Dynamically add joins for each nested level of the collection
            for i in range(1, depth + 1):
                reference_all_dataset_ids_select = reference_all_dataset_ids_select.join(
                    _dce_target_level_list[i],
                    _dce_target_level_list[i].dataset_collection_id
                    == _dce_target_level_list[i - 1].child_collection_id,
                )
            _leaf_target_dce_ref = _dce_target_level_list[-1]
            reference_all_dataset_ids_select = (
                reference_all_dataset_ids_select.join(
                    _hda_target_ref, _hda_target_ref.id == _leaf_target_dce_ref.hda_id
                )
                .where(_dce_target_root_ref.id == v)
                .distinct()
            )
            reference_all_dataset_ids_cte = reference_all_dataset_ids_select.cte(f"ref_all_ds_ids_{k}_{v}")

            # --- CTE: reference_dce_signature_elements_cte ---
            # This CTE generates a "path signature string" for each individual element
            # within the *reference* collection. This signature combines identifiers
            # from all levels of the collection and the dataset ID, providing a unique
            # identifier for each dataset's position within the collection structure.
            path_components = [
                _dce_target_root_ref.element_identifier,
                *[_dce_target_level_list[i].element_identifier for i in range(depth + 1)],
                _hda_target_ref.dataset_id.cast(sqlalchemy.Text),  # Ensure type for concat_ws
            ]

            reference_dce_signature_elements_select = (
                select(
                    func.concat_ws(";", *path_components).label("path_signature_string"),
                    _hda_target_ref.dataset_id.label("raw_dataset_id_for_ordering"),  # Keep original type for ordering
                )
                .select_from(_dce_target_root_ref)
                .join(
                    _dce_target_child_collection_ref,
                    _dce_target_child_collection_ref.id == _dce_target_root_ref.child_collection_id,
                )
                .join(
                    _dce_target_level_list[0],
                    _dce_target_level_list[0].dataset_collection_id == _dce_target_child_collection_ref.id,
                )
            )

            for i in range(1, depth + 1):
                reference_dce_signature_elements_select = reference_dce_signature_elements_select.join(
                    _dce_target_level_list[i],
                    _dce_target_level_list[i].dataset_collection_id
                    == _dce_target_level_list[i - 1].child_collection_id,
                )

            _leaf_target_dce_ref = _dce_target_level_list[-1]
            reference_dce_signature_elements_select = reference_dce_signature_elements_select.join(
                _hda_target_ref, _hda_target_ref.id == _leaf_target_dce_ref.hda_id
            ).where(_dce_target_root_ref.id == v)
            reference_dce_signature_elements_cte = reference_dce_signature_elements_select.cte(
                f"ref_dce_sig_els_{k}_{v}"
            )

            # --- CTE: reference_full_signature_cte ---
            # This CTE aggregates the path signatures and dataset IDs of the *reference*
            # collection into ordered arrays. These arrays form the "full signature"
            # used for direct comparison with candidate collections.
            reference_full_signature_cte = (
                select(
                    func.array_agg(
                        reference_dce_signature_elements_cte.c.path_signature_string,
                        order_by=reference_dce_signature_elements_cte.c.path_signature_string,
                    ).label("signature_array"),
                    func.array_agg(
                        reference_dce_signature_elements_cte.c.raw_dataset_id_for_ordering.cast(
                            sqlalchemy.Integer
                        ),  # Cast to Integer here
                        order_by=reference_dce_signature_elements_cte.c.path_signature_string,  # Order by full path to ensure consistency
                    ).label("ordered_dataset_id_array"),
                    func.count(reference_dce_signature_elements_cte.c.path_signature_string).label(
                        "element_count"
                    ),  # Count elements based on path_signature_string
                )
                .select_from(reference_dce_signature_elements_cte)
                .cte(f"ref_dce_full_sig_{k}_{v}")
            )

            # --- Aliases for Candidate Dataset Collection Structure ---
            # These aliases are used to represent potential matching dataset collections
            # in the database, which will be compared against the reference.
            candidate_dce_root = aliased(model.DatasetCollectionElement, name=f"candidate_dce_root_{k}_{v}")
            candidate_dce_child_collection = aliased(
                model.DatasetCollection, name=f"candidate_dce_child_collection_{k}_{v}"
            )
            candidate_dce_level_list = [
                aliased(model.DatasetCollectionElement, name=f"candidate_dce_level_{k}_{v}_{i}")
                for i in range(depth + 1)
            ]
            candidate_hda = aliased(model.HistoryDatasetAssociation, name=f"candidate_hda_{k}_{v}")
            candidate_history = aliased(model.History, name=f"candidate_history_{k}_{v}")

            # --- CTE: candidate_dce_pre_filter_ids_cte (Initial Candidate Filtering) ---
            # This CTE performs a first pass to quickly narrow down potential candidate
            # dataset collections. It checks for:
            # 1. Existence of a child collection (ensuring it's a collection, not a single HDA).
            # 2. User permissions (published or owned by the current user).
            # 3. Overlap in *any* dataset IDs with the reference collection.
            candidate_dce_pre_filter_ids_select = (
                select(candidate_dce_root.id.label("candidate_dce_id"))
                .distinct()
                .select_from(candidate_dce_root)
                .where(candidate_dce_root.child_collection_id.isnot(None))
                .join(
                    candidate_dce_child_collection,
                    candidate_dce_child_collection.id == candidate_dce_root.child_collection_id,
                )
                .join(
                    candidate_dce_level_list[0],
                    candidate_dce_level_list[0].dataset_collection_id == candidate_dce_child_collection.id,
                )
            )
            for i in range(1, depth + 1):
                candidate_dce_pre_filter_ids_select = candidate_dce_pre_filter_ids_select.join(
                    candidate_dce_level_list[i],
                    candidate_dce_level_list[i].dataset_collection_id
                    == candidate_dce_level_list[i - 1].child_collection_id,
                )
            _leaf_candidate_dce_pre = candidate_dce_level_list[-1]
            candidate_dce_pre_filter_ids_select = (
                candidate_dce_pre_filter_ids_select.join(
                    candidate_hda, candidate_hda.id == _leaf_candidate_dce_pre.hda_id
                )
                .join(candidate_history, candidate_history.id == candidate_hda.history_id)
                .where(or_(candidate_history.published == true(), candidate_history.user_id == user_id))
                .where(candidate_hda.dataset_id.in_(select(reference_all_dataset_ids_cte.c.ref_dataset_id_for_overlap)))
            )
            candidate_dce_pre_filter_ids_cte = candidate_dce_pre_filter_ids_select.cte(
                f"cand_dce_pre_filter_ids_{k}_{v}"
            )

            # --- CTE: candidate_dce_signature_elements_cte ---
            # This CTE calculates the path signature string and raw dataset ID for each
            # element within the *pre-filtered candidate* collections. This is similar
            # to the reference signature elements CTE but for the candidates.
            candidate_path_components_fixed = [
                candidate_dce_root.element_identifier,
                *[candidate_dce_level_list[i].element_identifier for i in range(depth + 1)],
                candidate_hda.dataset_id.cast(sqlalchemy.Text),  # Ensure type for concat_ws
            ]

            candidate_dce_signature_elements_select = (
                select(
                    candidate_dce_root.id.label("candidate_dce_id"),
                    func.concat_ws(";", *candidate_path_components_fixed).label("path_signature_string"),
                    candidate_hda.dataset_id.label("dataset_id_for_ordered_array"),  # This is now Integer
                )
                .select_from(candidate_dce_root)
                # Apply the initial filter here!
                .where(candidate_dce_root.id.in_(select(candidate_dce_pre_filter_ids_cte.c.candidate_dce_id)))
                .where(candidate_dce_root.child_collection_id.isnot(None))
                .join(
                    candidate_dce_child_collection,
                    candidate_dce_child_collection.id == candidate_dce_root.child_collection_id,
                )
                .join(
                    candidate_dce_level_list[0],
                    candidate_dce_level_list[0].dataset_collection_id == candidate_dce_child_collection.id,
                )
            )
            # Add dynamic joins for nested levels
            for i in range(1, depth + 1):
                candidate_dce_signature_elements_select = candidate_dce_signature_elements_select.join(
                    candidate_dce_level_list[i],
                    candidate_dce_level_list[i].dataset_collection_id
                    == candidate_dce_level_list[i - 1].child_collection_id,
                )

            _leaf_candidate_dce = candidate_dce_level_list[-1]
            candidate_dce_signature_elements_select = (
                candidate_dce_signature_elements_select.join(
                    candidate_hda, candidate_hda.id == _leaf_candidate_dce.hda_id
                )
                .join(candidate_history, candidate_history.id == candidate_hda.history_id)
                .where(or_(candidate_history.published == true(), candidate_history.user_id == user_id))
            )
            candidate_dce_signature_elements_cte = candidate_dce_signature_elements_select.cte(
                f"cand_dce_sig_els_{k}_{v}"
            )

            # --- CTE: candidate_pre_signatures_cte (Candidate Aggregation for Comparison) ---
            # This CTE aggregates the dataset IDs from the candidate collections into
            # ordered arrays, similar to `reference_full_signature_cte`. It also
            # counts the elements to ensure size consistency.
            candidate_pre_signatures_cte = (
                select(
                    candidate_dce_signature_elements_cte.c.candidate_dce_id,
                    # Corrected array_agg syntax: pass column directly, use order_by keyword
                    func.array_agg(
                        candidate_dce_signature_elements_cte.c.dataset_id_for_ordered_array.cast(
                            sqlalchemy.Integer
                        ),  # Cast explicitly
                        order_by=candidate_dce_signature_elements_cte.c.path_signature_string,  # Order by the full path
                    ).label("candidate_ordered_dataset_ids_array"),
                    func.count(candidate_dce_signature_elements_cte.c.candidate_dce_id).label(
                        "candidate_element_count"
                    ),
                )
                .select_from(candidate_dce_signature_elements_cte)
                .group_by(candidate_dce_signature_elements_cte.c.candidate_dce_id)
                .cte(f"cand_dce_pre_sig_{k}_{v}")
            )

            # --- CTE: filtered_cand_dce_by_dataset_ids_cte (Filtering by Element Count and Dataset ID Array) ---
            # This crucial CTE filters the candidate collections further by comparing:
            # 1. Their total element count with the reference collection's element count.
            # 2. Their ordered array of dataset IDs with the reference's ordered array.
            # This step ensures that candidate collections have the same number of elements
            # and contain the exact same datasets, in the same logical order (based on path).
            filtered_cand_dce_by_dataset_ids_cte = (
                select(candidate_pre_signatures_cte.c.candidate_dce_id)
                .select_from(candidate_pre_signatures_cte, reference_full_signature_cte)
                .where(
                    and_(
                        candidate_pre_signatures_cte.c.candidate_element_count
                        == reference_full_signature_cte.c.element_count,
                        candidate_pre_signatures_cte.c.candidate_ordered_dataset_ids_array
                        == reference_full_signature_cte.c.ordered_dataset_id_array,
                    )
                )
                .cte(f"filtered_cand_dce_{k}_{v}")
            )

            # --- CTE: final_candidate_signatures_cte (Final Full Signature Calculation for Matched Candidates) ---
            # For the candidates that passed the previous filtering, this CTE calculates
            # their full path signature array. This signature represents the complete
            # structural and content identity of the collection.
            final_candidate_signatures_cte = (
                select(
                    candidate_dce_signature_elements_cte.c.candidate_dce_id,
                    func.array_agg(
                        sqlalchemy.text(
                            f"{candidate_dce_signature_elements_cte.c.path_signature_string} ORDER BY {candidate_dce_signature_elements_cte.c.path_signature_string.name}"
                        )
                    ).label("full_signature_array"),
                )
                .select_from(candidate_dce_signature_elements_cte)
                .where(
                    candidate_dce_signature_elements_cte.c.candidate_dce_id.in_(
                        select(filtered_cand_dce_by_dataset_ids_cte.c.candidate_dce_id)
                    )
                )
                .group_by(candidate_dce_signature_elements_cte.c.candidate_dce_id)
                .cte(f"final_cand_dce_full_sig_{k}_{v}")
            )

            # --- Main Query Construction for Dataset Collection Elements ---
            # This section joins the main `stmt` (representing jobs) with the CTEs
            # to filter jobs whose input DCE matches the reference DCE's full signature.
            a = aliased(
                model.JobToInputDatasetCollectionElementAssociation, name=f"job_to_input_dce_association_{k}_{v}"
            )
            labeled_col = a.dataset_collection_element_id.label(f"{k}_{v}")
            stmt = stmt.add_columns(labeled_col)
            stmt = stmt.join(a, a.job_id == model.Job.id)

            input_dce = aliased(model.DatasetCollectionElement)

            stmt = stmt.join(
                input_dce,
                and_(
                    input_dce.id == a.dataset_collection_element_id,
                    # The final filter: ensure the input DCE's ID is among those candidates
                    # whose full signature array *exactly matches* the reference's signature array.
                    input_dce.id.in_(
                        select(final_candidate_signatures_cte.c.candidate_dce_id).where(
                            final_candidate_signatures_cte.c.full_signature_array
                            == select(reference_full_signature_cte.c.signature_array).scalar_subquery()
                        )
                    ),
                ),
            )

            data_conditions.append(a.name == k)
            used_ids.append(labeled_col)
            return stmt

        else:  # DCE points directly to an HDA (dce_root_target.hda_id is not None and child_collection_id is None)
            # For this simple case, the full signature array comparison for nested collections doesn't apply.
            # We can use a direct comparison of the HDA and element_identifier.
            # This logic needs to align with how this type of DCE was previously matched.

            # Aliases for the "left" side (job to input DCE path)
            a = aliased(
                model.JobToInputDatasetCollectionElementAssociation, name=f"job_to_input_dce_association_{k}_{v}"
            )
            dce_left = aliased(model.DatasetCollectionElement, name=f"dce_left_{k}_{v}")
            hda_left = aliased(model.HistoryDatasetAssociation, name=f"hda_left_{k}_{v}")

            # Aliases for the "right" side (target DCE path in the main query)
            dce_right = aliased(model.DatasetCollectionElement, name=f"dce_right_{k}_{v}")
            hda_right = aliased(model.HistoryDatasetAssociation, name=f"hda_right_{k}_{v}")

            # Start joins from job → input DCE association → first-level DCE (left side)
            labeled_col = a.dataset_collection_element_id.label(f"{k}_{v}")
            stmt = stmt.add_columns(labeled_col)
            stmt = stmt.join(a, a.job_id == model.Job.id)
            stmt = stmt.join(dce_left, dce_left.id == a.dataset_collection_element_id)
            stmt = stmt.join(hda_left, hda_left.id == dce_left.hda_id)  # Join to HDA for left side

            # Join to target DCE (v) directly (right side)
            stmt = stmt.join(dce_right, dce_right.id == v)
            stmt = stmt.join(hda_right, hda_right.id == dce_right.hda_id)  # Join to HDA for right side

            # Compare element identifiers and dataset IDs
            data_conditions.append(
                and_(
                    a.name == k,
                    dce_left.element_identifier == dce_right.element_identifier,
                    hda_left.dataset_id == hda_right.dataset_id,  # Direct dataset_id comparison
                )
            )
            used_ids.append(labeled_col)
            return stmt


def view_show_job(trans, job: Job, full: bool) -> Dict:
    is_admin = trans.user_is_admin
    job_dict = job.to_dict("element", system_details=is_admin)
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
            model.WorkflowInvocationStep.job_id,
            model.WorkflowInvocationStep.implicit_collection_jobs_id,
            model.WorkflowInvocationStep.state,
        )
        .select_from(join)
        .where(model.WorkflowInvocation.id == invocation_id)
    )
    for row in sa_session.execute(statement):
        if row[0]:
            yield ("Job", row[0], row[2])
        if row[1]:
            yield ("ImplicitCollectionJobs", row[1], row[2])


def get_job_metrics_for_invocation(sa_session: galaxy_scoped_session, invocation_id: int):
    single_job_stmnt = (
        select(WorkflowStep.order_index, Job.id, Job.tool_id, WorkflowStep.label, JobMetricNumeric)
        .join(Job, JobMetricNumeric.job_id == Job.id)
        .join(
            WorkflowInvocationStep,
            and_(
                WorkflowInvocationStep.workflow_invocation_id == invocation_id, WorkflowInvocationStep.job_id == Job.id
            ),
        )
        .join(WorkflowStep, WorkflowStep.id == WorkflowInvocationStep.workflow_step_id)
    )
    collection_job_stmnt = (
        select(WorkflowStep.order_index, Job.id, Job.tool_id, WorkflowStep.label, JobMetricNumeric)
        .join(Job, JobMetricNumeric.job_id == Job.id)
        .join(ImplicitCollectionJobsJobAssociation, Job.id == ImplicitCollectionJobsJobAssociation.job_id)
        .join(
            ImplicitCollectionJobs,
            ImplicitCollectionJobs.id == ImplicitCollectionJobsJobAssociation.implicit_collection_jobs_id,
        )
        .join(
            WorkflowInvocationStep,
            and_(
                WorkflowInvocationStep.workflow_invocation_id == invocation_id,
                WorkflowInvocationStep.implicit_collection_jobs_id == ImplicitCollectionJobs.id,
            ),
        )
        .join(WorkflowStep, WorkflowStep.id == WorkflowInvocationStep.workflow_step_id)
    )
    # should be sa_session.execute(single_job_stmnt.union(collection_job_stmnt)).all() but that returns
    # columns instead of the job metrics ORM instance.
    return sorted(
        (*sa_session.execute(single_job_stmnt).all(), *sa_session.execute(collection_job_stmnt).all()),
        key=lambda row: row[0],
    )


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
            invocation_state = sa_session.get(model.WorkflowInvocation, job_source_id).state
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
        job_summaries[job_id] = summarize_jobs_to_dict(sa_session, sa_session.get(Job, job_id))
    for implicit_collection_jobs_id in implicit_collection_job_ids:
        implicit_collection_jobs_summaries[implicit_collection_jobs_id] = summarize_jobs_to_dict(
            sa_session, sa_session.get(model.ImplicitCollectionJobs, implicit_collection_jobs_id)
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


class JobsSummary(TypedDict):
    populated_state: str
    states: Dict[str, int]
    model: str
    id: int


def summarize_jobs_to_dict(sa_session, jobs_source) -> Optional[JobsSummary]:
    """Produce a summary of jobs for job summary endpoints.

    :type   jobs_source: a Job or ImplicitCollectionJobs or None
    :param  jobs_source: the object to summarize

    :rtype:     dict
    :returns:   dictionary containing job summary information
    """
    rval: Optional[JobsSummary] = None
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
            "states": {},
        }
        if populated_state == "ok":
            # produce state summary...
            join = model.ImplicitCollectionJobs.table.join(
                model.ImplicitCollectionJobsJobAssociation.table.join(model.Job)
            )
            statement = (
                select(model.Job.state, func.count())
                .select_from(join)
                .where(model.ImplicitCollectionJobs.id == jobs_source.id)
                .group_by(model.Job.state)
            )
            for row in sa_session.execute(statement):
                rval["states"][row[0]] = row[1]
    return rval


def summarize_job_metrics(trans, job):
    """Produce a dict-ified version of job metrics ready for tabular rendering.

    Precondition: the caller has verified the job is accessible to the user
    represented by the trans parameter.
    """
    return summarize_metrics(trans, job.metrics)


def summarize_metrics(trans: ProvidesUserContext, job_metrics):
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
        for m in job_metrics
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
    if job_destination_params := job.destination_params:
        destination_params.update(job_destination_params)
    return destination_params


def summarize_job_parameters(trans: ProvidesUserContext, job: Job):
    """Produce a dict-ified version of job parameters ready for tabular rendering.

    Precondition: the caller has verified the job is accessible to the user
    represented by the trans parameter.
    """
    # More client logic here than is ideal but it is hard to reason about
    # tool parameter types on the client relative to the server.

    def inputs_recursive(input_params, param_values, depth=1, upgrade_messages=None):
        if upgrade_messages is None:
            upgrade_messages = {}

        rval = []

        for input in input_params.values():
            if input.name in param_values:
                input_value = param_values[input.name]
                if input.type == "repeat":
                    for i in range(len(input_value)):
                        rval.extend(inputs_recursive(input.inputs, input_value[i], depth=depth + 1))
                elif input.type == "section":
                    # Get the value of the current Section parameter
                    rval.append(dict(text=input.name, depth=depth))
                    rval.extend(
                        inputs_recursive(
                            input.inputs,
                            input_value,
                            depth=depth + 1,
                            upgrade_messages=upgrade_messages.get(input.name),
                        )
                    )
                elif input.type == "conditional":
                    try:
                        current_case = input_value["__current_case__"]
                        is_valid = True
                    except Exception:
                        current_case = None
                        is_valid = False
                    if is_valid:
                        rval.append(
                            dict(
                                text=input.test_param.label or input.test_param.name,
                                depth=depth,
                                value=input.cases[current_case].value,
                            )
                        )
                        rval.extend(
                            inputs_recursive(
                                input.cases[current_case].inputs,
                                input_value,
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
                            value=f"{len(input_value)} uploaded datasets",
                        )
                    )
                elif (
                    input.type == "data"
                    or input.type == "data_collection"
                    or isinstance(input_value, model.HistoryDatasetAssociation)
                ):
                    value: List[Union[Dict[str, Any], None]] = []
                    for element in listify(input_value):
                        if isinstance(element, model.HistoryDatasetAssociation):
                            hda = element
                            value.append({"src": "hda", "id": element.id, "hid": hda.hid, "name": hda.name})
                        elif isinstance(element, model.DatasetCollectionElement):
                            value.append({"src": "dce", "id": element.id, "name": element.element_identifier})
                        elif isinstance(element, model.HistoryDatasetCollectionAssociation):
                            value.append({"src": "hdca", "id": element.id, "hid": element.hid, "name": element.name})
                        elif element is None:
                            value.append(None)
                        else:
                            raise Exception(
                                f"Unhandled data input parameter type encountered {element.__class__.__name__}"
                            )
                    rval.append(dict(text=input.label or input.name, depth=depth, value=value))
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
                            value=input.value_to_display_text(input_value),
                            notes=upgrade_messages.get(input.name, ""),
                        )
                    )
            else:
                # Parameter does not have a stored value.
                # Get parameter label.
                if input.type == "conditional":
                    label = input.test_param.label
                else:
                    label = input.label or input.name
                rval.append(
                    dict(text=label, depth=depth, notes="not used (parameter was added after this job was run)")
                )

        return rval

    # Load the tool
    app = trans.app
    toolbox = app.toolbox
    tool_uuid = None
    if dynamic_tool := job.dynamic_tool:
        tool_uuid = dynamic_tool.uuid
    tool = toolbox.get_tool(job.tool_id, job.tool_version, tool_uuid=tool_uuid, user=trans.user)

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
        "outputs": summarize_job_outputs(job=job, tool=tool, params=params_objects),
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


def summarize_job_outputs(job: model.Job, tool, params):
    outputs = defaultdict(list)
    output_labels = {}
    possible_outputs = (
        ("hda", "dataset_id", job.output_datasets),
        ("ldda", "ldda_id", job.output_library_datasets),
        ("hdca", "dataset_collection_id", job.output_dataset_collection_instances),
    )
    for src, attribute, output_associations in possible_outputs:
        output_associations = cast(List, output_associations)  # during iteration, mypy sees it as object
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
                    "value": {"src": src, "id": getattr(output_association, attribute)},
                }
            )
    return outputs


def get_jobs_to_check_at_startup(session: galaxy_scoped_session, track_jobs_in_database: bool, config):
    if track_jobs_in_database:
        in_list = (Job.states.QUEUED, Job.states.RUNNING, Job.states.STOPPED)
    else:
        in_list = (Job.states.NEW, Job.states.QUEUED, Job.states.RUNNING)

    stmt = (
        select(Job)
        .execution_options(yield_per=YIELD_PER_ROWS)
        .filter(Job.state.in_(in_list) & (Job.handler == config.server_name))
    )
    if config.user_activation_on:
        # Filter out the jobs of inactive users.
        stmt = stmt.outerjoin(User).filter(or_((Job.user_id == null()), (User.active == true())))

    return session.scalars(stmt).all()


def get_job(session: galaxy_scoped_session, *where_clauses):
    stmt = select(Job).where(*where_clauses).limit(1)
    return session.scalars(stmt).first()
