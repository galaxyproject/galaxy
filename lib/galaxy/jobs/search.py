import json
from six import string_types
from sqlalchemy import and_, or_
from sqlalchemy.orm import aliased

from galaxy import model
from galaxy.managers.hdas import HDAManager
from galaxy.managers.collections import DatasetCollectionManager
from galaxy.managers.lddas import LDDAManager


class JobSearch(object):
    """Search for jobs using tool inputs or other jobs"""
    def __init__(self, app):
        self.app = app
        self.sa_session = app.model.context
        self.hda_manager = HDAManager(app)
        self.dataset_collection_manager = DatasetCollectionManager(app)
        self.ldda_manager = LDDAManager(app)
        self.decode_id = self.app.security.decode_id

    def by_tool_input(self, trans, tool_id, inputs, job_state='ok'):
        """Search for jobs producing same results using the 'inputs' part of a tool POST."""
        user = trans.user
        input_param = {}
        input_data = {}
        for k, v in inputs.items():
            if isinstance(v, dict):
                if 'id' in v:
                    decoded_id = self.decode_id(v['id'])
                    src = v.get('src', 'hda')
                    if src == 'hda':
                        all_items = self._get_all_hdas(trans=trans, hda_id=decoded_id)
                        if not self.one_not_deleted(all_items):
                            return []
                    elif src == 'ldda':
                        all_items = self._get_all_lddas(trans=trans, ldda_id=v['id'])
                        if not self.one_not_deleted(all_items):
                            return []
                    elif src == 'hdca':
                        all_items = self._get_all_hdcas(trans=trans, hdca_id=v['id'])
                        if self.one_not_deleted(all_items):
                            if any((True for hda in all_items[0].dataset_instances if hda.deleted)):
                                return []
                        else:
                            return []
                    input_data[k] = {src: {item.id for item in all_items}}
            else:
                input_param[k] = json.dumps(str(v))
        return self.__search(tool_id=tool_id, user=user, input_param=input_param, input_data=input_data, job_state=job_state)

    def one_not_deleted(self, items):
        return any((True for item in items if not item.deleted))

    def _get_all_hdas(self, trans, hda_id):
        """Given a decoded `hda_id`, find other instances that refer to the same dataset."""
        hda = self.hda_manager.get_accessible(hda_id, trans.user)
        return self.sa_session.query(model.HistoryDatasetAssociation).filter(
            model.HistoryDatasetAssociation.dataset_id == hda.dataset_id).all()

    def _get_all_lddas(self, trans, ldda_id):
        """Given a decoded `ldda_id` return the corresponding ldda"""
        # TODO: implement looking up HDAs that point to the same dataset
        ldda = self.ldda_manager.get(trans=trans, id=ldda_id)
        return [ldda]

    def _get_all_hdcas(self, trans, hdca_id):
        """Given an hdca, returns a list of other hdcas that were copied from this hdca."""
        # TODO: would be great if we can find all identical hdcas
        hdca = self.dataset_collection_manager.get_dataset_collection_instance(trans=trans,
                                                                               instance_type='history',
                                                                               id=hdca_id)
        copied_from = getattr(hdca, 'copied_from_history_dataset_collection_association', None)
        hdcas = [hdca]
        if copied_from:
            hdcas.append(copied_from)
        return hdcas

    def __search(self, tool_id, user, input_param, input_data, job_state=None):

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

        for k, v in input_param.items():
            a = aliased(model.JobParameter)
            if isinstance(v, string_types):
                query = query.filter(and_(
                    model.Job.id == a.job_id,
                    a.name == k,
                    a.value == v
                ))
        for k, type_values in input_data.items():
            for t, v in type_values.items():
                if t == 'hda':
                    a = aliased(model.JobToInputDatasetAssociation)
                    query = query.filter(and_(
                        model.Job.id == a.job_id,
                        a.name == k,
                        a.dataset_id.in_(v)
                    ))
                elif t == 'ldda':
                        a = aliased(model.JobToInputDatasetCollectionAssociation)
                        query = query.filter(and_(
                            model.Job.id == a.job_id,
                            a.name == k,
                            a.ldda_id.in_(v)
                        ))
                elif t == 'hdca':
                    a = aliased(model.JobToInputLibraryDatasetAssociation)
                    query = query.filter(and_(
                        model.Job.id == a.job_id,
                        a.name == k,
                        a.dataset_collection_id.in_(v)
                    ))
                else:
                    return []

        jobs = []
        for job in query.all():
            # check to make sure none of the output datasets or collections have been deleted
            # TODO: find copies if output is deleted
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
                jobs.append(job)
        return jobs
