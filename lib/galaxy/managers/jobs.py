import json
import logging

from boltons.iterutils import remap
from six import string_types
from sqlalchemy import and_, false, or_
from sqlalchemy.orm import aliased

from galaxy import model
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

    def by_tool_input(self, trans, tool_id, param_dump=None, job_state='ok', is_workflow_step=False):
        """Search for jobs producing same results using the 'inputs' part of a tool POST."""
        user = trans.user
        input_data = defaultdict(list)
        input_ids = defaultdict(dict)

        def populate_input_data_input_id(path, key, value):
            """Traverses expanded incoming using remap and collects input_ids and input_data."""
            if key == 'id':
                path_key = get_path_key(path[:-2])
                current_case = param_dump
                for p in path:
                    current_case = current_case[p]
                src = current_case['src']
                input_data[path_key].append({'src': src, 'id': value})
                input_ids[src][value] = True
                return key, value
            return key, value

        remap(param_dump, visit=populate_input_data_input_id)
        return self.__search(tool_id=tool_id,
                             user=user,
                             input_data=input_data,
                             job_state=job_state,
                             param_dump=param_dump,
                             input_ids=input_ids,
                             is_workflow_step=is_workflow_step)

    def __search(self, tool_id, user, input_data, input_ids=None, job_state=None, param_dump=None, is_workflow_step=False):
        search_timer = ExecutionTimer()
        query = self.sa_session.query(model.Job).filter(
            model.Job.tool_id == tool_id,
            model.Job.user == user
        )

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
                if t == 'hda':
                    a = aliased(model.JobToInputDatasetAssociation)
                    b = aliased(model.HistoryDatasetAssociation)
                    c = aliased(model.HistoryDatasetAssociation)
                    query = query.filter(and_(
                        model.Job.id == a.job_id,
                        a.name == k,
                        a.dataset_id == b.id,
                        c.dataset_id == b.dataset_id,
                        c.id == v,
                        or_(b.deleted == false(), c.deleted == false())
                    ))
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
                        or_(and_(b.deleted == false(), b.id == v),
                            and_(or_(c.copied_from_history_dataset_collection_association_id == b.id,
                                     b.copied_from_history_dataset_collection_association_id == c.id),
                                 c.deleted == false()
                                 )
                            )
                    ))
                else:
                    return []

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
            if is_workflow_step:
                add_n_parameters = 3
            else:
                add_n_parameters = 2
            if not len(job.parameters) == (len(new_param_dump) + add_n_parameters):
                # Verify that equivalent jobs had the same number of job parameters
                # We add 2 or 3 to new_param_dump because chrominfo and dbkey (and __workflow_invocation_uuid__) are not passed
                # as input parameters
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
