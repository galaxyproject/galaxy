import json
import logging

from boltons.iterutils import remap
from six import string_types
from sqlalchemy import and_, false, func, or_
from sqlalchemy.orm import aliased
from sqlalchemy.sql import select

from galaxy import model
from galaxy.exceptions import RequestParameterInvalidException
from galaxy.managers.collections import DatasetCollectionManager
from galaxy.managers.hdas import HDAManager
from galaxy.managers.lddas import LDDAManager
from galaxy.util import (
    defaultdict,
    ExecutionTimer
)

log = logging.getLogger(__name__)


def get_path_key(path_tuple):
    path_key = ""
    tuple_elements = len(path_tuple)
    for i, p in enumerate(path_tuple):
        if isinstance(p, int):
            sep = '_'
        else:
            sep = '|'
        if i == (tuple_elements - 2) and p == 'values':
            # dataset inputs are always wrapped in lists. To avoid 'rep_factorName_0|rep_factorLevel_2|countsFile|values_0',
            # we remove the last 2 items of the path tuple (values and list index)
            return path_key
        if path_key:
            path_key = "%s%s%s" % (path_key, sep, p)
        else:
            path_key = p
    return path_key


class JobSearch(object):
    """Search for jobs using tool inputs or other jobs"""
    def __init__(self, app):
        self.app = app
        self.sa_session = app.model.context
        self.hda_manager = HDAManager(app)
        self.dataset_collection_manager = DatasetCollectionManager(app)
        self.ldda_manager = LDDAManager(app)
        self.decode_id = self.app.security.decode_id

    def by_tool_input(self, trans, tool_id, tool_version, param=None, param_dump=None, job_state='ok'):
        """Search for jobs producing same results using the 'inputs' part of a tool POST."""
        user = trans.user
        input_data = defaultdict(list)

        def populate_input_data_input_id(path, key, value):
            """Traverses expanded incoming using remap and collects input_ids and input_data."""
            if key == 'id':
                path_key = get_path_key(path[:-2])
                current_case = param_dump
                for p in path:
                    current_case = current_case[p]
                src = current_case['src']
                current_case = param
                for i, p in enumerate(path):
                    if p == 'values' and i == len(path) - 2:
                        continue
                    if isinstance(current_case, (list, dict)):
                        current_case = current_case[p]
                identifier = getattr(current_case, "element_identifier", None)
                input_data[path_key].append({'src': src,
                                             'id': value,
                                             'identifier': identifier,
                                             })
                return key, "__id_wildcard__"
            return key, value

        wildcard_param_dump = remap(param_dump, visit=populate_input_data_input_id)
        return self.__search(tool_id=tool_id,
                             tool_version=tool_version,
                             user=user,
                             input_data=input_data,
                             job_state=job_state,
                             param_dump=param_dump,
                             wildcard_param_dump=wildcard_param_dump)

    def __search(self, tool_id, tool_version, user, input_data, job_state=None, param_dump=None, wildcard_param_dump=None):
        search_timer = ExecutionTimer()

        def replace_dataset_ids(path, key, value):
            """Exchanges dataset_ids (HDA, LDA, HDCA, not Dataset) in param_dump with dataset ids used in job."""
            if key == 'id':
                current_case = param_dump
                for p in path:
                    current_case = current_case[p]
                src = current_case['src']
                value = job_input_ids[src][value]
                return key, value
            return key, value

        conditions = [and_(model.Job.tool_id == tool_id,
                           model.Job.user == user)]

        if tool_version:
            conditions.append(model.Job.tool_version == str(tool_version))

        if job_state is None:
            conditions.append(
                model.Job.state.in_([model.Job.states.NEW,
                                     model.Job.states.QUEUED,
                                     model.Job.states.WAITING,
                                     model.Job.states.RUNNING,
                                     model.Job.states.OK])
            )
        else:
            if isinstance(job_state, string_types):
                conditions.append(model.Job.state == job_state)
            elif isinstance(job_state, list):
                o = []
                for s in job_state:
                    o.append(model.Job.state == s)
                conditions.append(
                    or_(*o)
                )

        # We now build the query filters that relate to the input datasets
        # that this job uses. We keep track of the requested dataset id in `requested_ids`,
        # the type (hda, hdca or lda) in `data_types`
        # and the ids that have been used in the job that has already been run in `used_ids`.
        requested_ids = []
        data_types = []
        used_ids = []
        for k, input_list in input_data.items():
            for type_values in input_list:
                t = type_values['src']
                v = type_values['id']
                requested_ids.append(v)
                data_types.append(t)
                identifier = type_values['identifier']
                if t == 'hda':
                    a = aliased(model.JobToInputDatasetAssociation)
                    b = aliased(model.HistoryDatasetAssociation)
                    c = aliased(model.HistoryDatasetAssociation)
                    d = aliased(model.JobParameter)
                    e = aliased(model.HistoryDatasetAssociationHistory)
                    conditions.append(and_(
                        model.Job.id == a.job_id,
                        a.name == k,
                        a.dataset_id == b.id,  # b is the HDA use for the job
                        c.dataset_id == b.dataset_id,
                        c.id == v,  # c is the requested job input HDA
                        # We need to make sure that the job we are looking for has been run with identical inputs.
                        # Here we deal with 3 requirements:
                        #  - the jobs' input dataset (=b) version is 0, meaning the job's input dataset is not yet ready
                        #  - b's update_time is older than the job create time, meaning no changes occurred
                        #  - the job has a dataset_version recorded, and that versions' metadata matches c's metadata.
                        or_(
                            and_(or_(a.dataset_version.in_([0, b.version]),
                                     b.update_time < model.Job.create_time),
                                 b.name == c.name,
                                 b.extension == c.extension,
                                 b.metadata == c.metadata,
                                 ),
                            and_(b.id == e.history_dataset_association_id,
                                 a.dataset_version == e.version,
                                 e.name == c.name,
                                 e.extension == c.extension,
                                 e._metadata == c._metadata,
                                 ),
                        ),
                        or_(b.deleted == false(), c.deleted == false())
                    ))
                    if identifier:
                        conditions.append(and_(model.Job.id == d.job_id,
                                             d.name == "%s|__identifier__" % k,
                                             d.value == json.dumps(identifier)))
                    used_ids.append(a.dataset_id)
                elif t == 'ldda':
                    a = aliased(model.JobToInputLibraryDatasetAssociation)
                    conditions.append(and_(
                        model.Job.id == a.job_id,
                        a.name == k,
                        a.ldda_id == v
                    ))
                    used_ids.append(a.ldda_id)
                elif t == 'hdca':
                    a = aliased(model.JobToInputDatasetCollectionAssociation)
                    b = aliased(model.HistoryDatasetCollectionAssociation)
                    c = aliased(model.HistoryDatasetCollectionAssociation)
                    conditions.append(and_(
                        model.Job.id == a.job_id,
                        a.name == k,
                        b.id == a.dataset_collection_id,
                        c.id == v,
                        b.name == c.name,
                        or_(and_(b.deleted == false(), b.id == v),
                            and_(or_(c.copied_from_history_dataset_collection_association_id == b.id,
                                     b.copied_from_history_dataset_collection_association_id == c.id),
                                 c.deleted == false(),
                                 )
                            )
                    ))
                    used_ids.append(a.dataset_collection_id)
                else:
                    return []

        for k, v in wildcard_param_dump.items():
            wildcard_value = json.dumps(v, sort_keys=True).replace('"id": "__id_wildcard__"', '"id": %')
            a = aliased(model.JobParameter)
            conditions.append(and_(
                model.Job.id == a.job_id,
                a.name == k,
                a.value.like(wildcard_value)
            ))

        conditions.append(and_(
            model.Job.any_output_dataset_collection_instances_deleted == false(),
            model.Job.any_output_dataset_deleted == false()
        ))

        query = self.sa_session.query(model.Job.id, *used_ids).filter(and_(*conditions))
        for job in query.all():
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
                    a = aliased(model.JobParameter)
                    job_parameter_conditions.append(and_(
                        a.name == k,
                        a.value == json.dumps(v, sort_keys=True)
                    ))
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
                if parameter.name in {'__workflow_invocation_uuid__', 'chromInfo', 'dbkey'} or parameter.name.endswith('|__identifier__'):
                    continue
                n_parameters += 1
            if not n_parameters == len(param_dump):
                continue
            log.info("Found equivalent job %s", search_timer)
            return job
        log.info("No equivalent jobs found %s", search_timer)
        return None


def fetch_job_states(app, sa_session, job_source_ids, job_source_types):
    decode = app.security.decode_id
    assert len(job_source_ids) == len(job_source_types)
    job_ids = set()
    implicit_collection_job_ids = set()

    for job_source_id, job_source_type in zip(job_source_ids, job_source_types):
        if job_source_type == "Job":
            job_ids.add(job_source_id)
        elif job_source_type == "ImplicitCollectionJobs":
            implicit_collection_job_ids.add(job_source_id)
        else:
            raise RequestParameterInvalidException("Invalid job source type %s found." % job_source_type)

    # TODO: use above sets and optimize queries on second pass.
    rval = []
    for job_source_id, job_source_type in zip(job_source_ids, job_source_types):
        if job_source_type == "Job":
            rval.append(summarize_jobs_to_dict(sa_session, sa_session.query(model.Job).get(decode(job_source_id))))
        else:
            rval.append(summarize_jobs_to_dict(sa_session, sa_session.query(model.ImplicitCollectionJobs).get(decode(job_source_id))))

    return rval


def summarize_jobs_to_dict(sa_session, jobs_source):
    """Proudce a summary of jobs for job summary endpoints.

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
            statement = select(
                [model.Job.state, func.count("*")]
            ).select_from(
                join
            ).where(
                model.ImplicitCollectionJobs.id == jobs_source.id
            ).group_by(
                model.Job.state
            )
            for row in sa_session.execute(statement):
                states[row[0]] = row[1]
            rval["states"] = states
    return rval
