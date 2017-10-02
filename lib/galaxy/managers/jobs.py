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
        input_ids = defaultdict(list)

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
                input_ids[src].append(value)
                return key, "__id_wildcard__"
            return key, value

        wildcard_param_dump = remap(param_dump, visit=populate_input_data_input_id)
        return self.__search(tool_id=tool_id,
                             tool_version=tool_version,
                             user=user,
                             input_data=input_data,
                             job_state=job_state,
                             param_dump=param_dump,
                             wildcard_param_dump=wildcard_param_dump,
                             input_ids=input_ids)

    def __search(self, tool_id, tool_version, user, input_data, input_ids=None, job_state=None, param_dump=None, wildcard_param_dump=None):
        search_timer = ExecutionTimer()
        query = self.sa_session.query(model.Job).filter(
            model.Job.tool_id == tool_id,
            model.Job.user == user
        )
        if tool_version:
            query = query.filter(model.Job.tool_version == str(tool_version))

        if job_state is None:
            query = query.filter(
                or_(
                    model.Job.state == 'running',
                    model.Job.state == 'queued',
                    model.Job.state == 'waiting',
                    model.Job.state == 'running',
                    model.Job.state == 'ok',
                )
            )
        else:
            if isinstance(job_state, string_types):
                query = query.filter(model.Job.state == job_state)
            elif isinstance(job_state, list):
                o = []
                for s in job_state:
                    o.append(model.Job.state == s)
                query = query.filter(
                    or_(*o)
                )

        for k, input_list in input_data.items():
            for type_values in input_list:
                t = type_values['src']
                v = type_values['id']
                identifier = type_values['identifier']
                if t == 'hda':
                    a = aliased(model.JobToInputDatasetAssociation)
                    b = aliased(model.HistoryDatasetAssociation)
                    c = aliased(model.HistoryDatasetAssociation)
                    d = aliased(model.JobParameter)
                    query = query.filter(and_(
                        model.Job.id == a.job_id,
                        a.name == k,
                        a.dataset_id == b.id,
                        c.dataset_id == b.dataset_id,
                        c.id == v,  # c is the requested job input HDA
                        # We can only compare input dataset names and metadata for a job
                        # if we know that the input dataset hasn't changed since the job was run.
                        # This is relatively strict, we may be able to lift this requirement if we record the jobs'
                        # relevant parameters as JobParameters in the database
                        b.update_time < model.Job.create_time,
                        b.name == c.name,
                        b.extension == c.extension,
                        b.metadata == c.metadata,
                        or_(b.deleted == false(), c.deleted == false())
                    ))
                    if identifier:
                        query = query.filter(model.Job.id == d.job_id,
                                             d.name == "%s|__identifier__" % k,
                                             d.value == json.dumps(identifier))
                elif t == 'ldda':
                        a = aliased(model.JobToInputLibraryDatasetAssociation)
                        query = query.filter(and_(
                            model.Job.id == a.job_id,
                            a.name == k,
                            a.ldda_id == v
                        ))
                elif t == 'hdca':
                    a = aliased(model.JobToInputDatasetCollectionAssociation)
                    b = aliased(model.HistoryDatasetCollectionAssociation)
                    c = aliased(model.HistoryDatasetCollectionAssociation)
                    query = query.filter(and_(
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
                else:
                    return []

        for k, v in wildcard_param_dump.items():
            test = json.dumps(v).replace('"id": "__id_wildcard__"', '"id": %')
            a = aliased(model.JobParameter)
            query = query.filter(and_(
                model.Job.id == a.job_id,
                a.name == k,
                a.value.like(test)
            ))

        for job in query.all():
            # We found a job that is equal in terms of tool_id, user, state and input datasets,
            # but to be able to verify that the parameters match we need to modify all instances of
            # dataset_ids (HDA, LDDA, HDCA) in the incoming param_dump to point to those used by the
            # possibly equivalent job, which may have been run on copies of the original input data.
            replacement_timer = ExecutionTimer()
            job_input_ids = {}
            for src, items in input_ids.items():
                for dataset_id in items:
                    if src in job_input_ids and dataset_id in job_input_ids[src]:
                        continue
                    if src == 'hda':
                        a = aliased(model.JobToInputDatasetAssociation)
                        b = aliased(model.HistoryDatasetAssociation)
                        c = aliased(model.HistoryDatasetAssociation)

                        (job_dataset_id,) = self.sa_session.query(b.id).filter(
                            and_(
                                a.job_id == job.id,
                                b.id == a.dataset_id,
                                c.dataset_id == b.dataset_id,
                                c.id == dataset_id
                            )
                        ).first()
                    elif src == 'hdca':
                        a = aliased(model.JobToInputDatasetCollectionAssociation)
                        b = aliased(model.HistoryDatasetCollectionAssociation)
                        c = aliased(model.HistoryDatasetCollectionAssociation)

                        (job_dataset_id,) = self.sa_session.query(b.id).filter(
                            and_(
                                a.job_id == job.id,
                                b.id == a.dataset_collection_id,
                                c.id == dataset_id,
                                or_(b.id == c.id, or_(c.copied_from_history_dataset_collection_association_id == b.id,
                                                      b.copied_from_history_dataset_collection_association_id == c.id)
                                    )
                            )
                        ).first()
                    elif src == 'ldda':
                        job_dataset_id = dataset_id
                    else:
                        return []
                    if src not in job_input_ids:
                        job_input_ids[src] = {dataset_id: job_dataset_id}
                    else:
                        job_input_ids[src][dataset_id] = job_dataset_id

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

            new_param_dump = remap(param_dump, visit=replace_dataset_ids)
            log.info("Parameter replacement finished %s", replacement_timer)
            # new_param_dump has its dataset ids remapped to those used by the job.
            # We now ask if the remapped job parameters match the current job.
            query = self.sa_session.query(model.Job).filter(model.Job.id == job.id)
            for k, v in new_param_dump.items():
                a = aliased(model.JobParameter)
                query = query.filter(and_(
                    a.job_id == job.id,
                    a.name == k,
                    a.value == json.dumps(v)
                ))
            if query.first() is None:
                continue
            n_parameters = 0
            # Verify that equivalent jobs had the same number of job parameters
            # We skip chrominfo, dbkey, __workflow_invocation_uuid__ and identifer
            # parameter as these are not passed along when expanding tool parameters
            # and they can differ without affecting the resulting dataset (when referencing identifier
            # in the tool xml this may not be entirely true).
            for parameter in job.parameters:
                if parameter.name in {'__workflow_invocation_uuid__', 'chromInfo', 'dbkey'} or parameter.name.endswith('|__identifier__'):
                    continue
                n_parameters += 1
            if not n_parameters == len(new_param_dump):
                continue
            # check to make sure none of the output datasets or collections have been deleted
            # TODO: refactors this into the initial job query
            outputs_deleted = False
            for hda in job.output_datasets:
                if hda.dataset.deleted:
                    outputs_deleted = True
                    break
            if not outputs_deleted:
                for collection_instance in job.output_dataset_collection_instances:
                    if collection_instance.dataset_collection_instance.deleted:
                        outputs_deleted = True
                        break
            if not outputs_deleted:
                log.info("Searching jobs finished %s", search_timer)
                return job
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
