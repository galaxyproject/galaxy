"""
API operations on a jobs.

.. seealso:: :class:`galaxy.model.Jobs`
"""

import json
import logging

from six import string_types
from sqlalchemy import and_, or_
from sqlalchemy.orm import aliased

from galaxy import exceptions
from galaxy import managers
from galaxy import model
from galaxy import util
from galaxy.web import _future_expose_api as expose_api
from galaxy.web import _future_expose_api_anonymous as expose_api_anonymous
from galaxy.web.base.controller import BaseAPIController
from galaxy.web.base.controller import UsesLibraryMixinItems

log = logging.getLogger(__name__)


class JobController(BaseAPIController, UsesLibraryMixinItems):

    def __init__(self, app):
        super(JobController, self).__init__(app)
        self.hda_manager = managers.hdas.HDAManager(app)
        self.dataset_collection_manager = managers.collections.DatasetCollectionManager(app)
        self.dataset_manager = managers.datasets.DatasetManager(app)

    @expose_api
    def index(self, trans, **kwd):
        """
        index( trans, state=None, tool_id=None, history_id=None, date_range_min=None, date_range_max=None, user_details=False )
        * GET /api/jobs:
            return jobs for current user

            !! if user is admin and user_details is True, then
                return jobs for all galaxy users based on filtering - this is an extended service

        :type   state: string or list
        :param  state: limit listing of jobs to those that match one of the included states. If none, all are returned.
        Valid Galaxy job states include:
                'new', 'upload', 'waiting', 'queued', 'running', 'ok', 'error', 'paused', 'deleted', 'deleted_new'

        :type   tool_id: string or list
        :param  tool_id: limit listing of jobs to those that match one of the included tool_ids. If none, all are returned.

        :type   user_details: boolean
        :param  user_details: if true, and requestor is an admin, will return external job id and user email.

        :type   date_range_min: string '2014-01-01'
        :param  date_range_min: limit the listing of jobs to those updated on or after requested date

        :type   date_range_max: string '2014-12-31'
        :param  date_range_max: limit the listing of jobs to those updated on or before requested date

        :type   history_id: string
        :param  history_id: limit listing of jobs to those that match the history_id. If none, all are returned.

        :rtype:     list
        :returns:   list of dictionaries containing summary job information
        """
        state = kwd.get('state', None)
        is_admin = trans.user_is_admin()
        user_details = kwd.get('user_details', False)

        if is_admin:
            query = trans.sa_session.query(trans.app.model.Job)
        else:
            query = trans.sa_session.query(trans.app.model.Job).filter(trans.app.model.Job.user == trans.user)

        def build_and_apply_filters(query, objects, filter_func):
            if objects is not None:
                if isinstance(objects, string_types):
                    query = query.filter(filter_func(objects))
                elif isinstance(objects, list):
                    t = []
                    for obj in objects:
                        t.append(filter_func(obj))
                    query = query.filter(or_(*t))
            return query

        query = build_and_apply_filters(query, state, lambda s: trans.app.model.Job.state == s)

        query = build_and_apply_filters(query, kwd.get('tool_id', None), lambda t: trans.app.model.Job.tool_id == t)
        query = build_and_apply_filters(query, kwd.get('tool_id_like', None), lambda t: trans.app.model.Job.tool_id.like(t))

        query = build_and_apply_filters(query, kwd.get('date_range_min', None), lambda dmin: trans.app.model.Job.table.c.update_time >= dmin)
        query = build_and_apply_filters(query, kwd.get('date_range_max', None), lambda dmax: trans.app.model.Job.table.c.update_time <= dmax)

        history_id = kwd.get('history_id', None)
        if history_id is not None:
            try:
                decoded_history_id = self.decode_id(history_id)
                query = query.filter(trans.app.model.Job.history_id == decoded_history_id)
            except:
                raise exceptions.ObjectAttributeInvalidException()

        out = []
        if kwd.get('order_by') == 'create_time':
            order_by = trans.app.model.Job.create_time.desc()
        else:
            order_by = trans.app.model.Job.update_time.desc()
        for job in query.order_by(order_by).all():
            job_dict = job.to_dict('collection', system_details=is_admin)
            j = self.encode_all_ids(trans, job_dict, True)
            if user_details:
                j['user_email'] = job.user.email
            out.append(j)

        return out

    @expose_api
    def show(self, trans, id, **kwd):
        """
        show( trans, id )
        * GET /api/jobs/{id}:
            return jobs for current user

        :type   id: string
        :param  id: Specific job id

        :type   full: boolean
        :param  full: whether to return extra information

        :rtype:     dictionary
        :returns:   dictionary containing full description of job data
        """
        job = self.__get_job(trans, id)
        is_admin = trans.user_is_admin()
        job_dict = self.encode_all_ids(trans, job.to_dict('element', system_details=is_admin), True)
        full_output = util.asbool(kwd.get('full', 'false'))
        if full_output:
            job_dict.update(dict(stderr=job.stderr, stdout=job.stdout))
            if is_admin:
                job_dict['user_email'] = job.user.email

                def metric_to_dict(metric):
                    metric_name = metric.metric_name
                    metric_value = metric.metric_value
                    metric_plugin = metric.plugin
                    title, value = trans.app.job_metrics.format(metric_plugin, metric_name, metric_value)
                    return dict(
                        title=title,
                        value=value,
                        plugin=metric_plugin,
                        name=metric_name,
                        raw_value=str(metric_value),
                    )

                job_dict['job_metrics'] = [metric_to_dict(metric) for metric in job.metrics]
        return job_dict

    @expose_api
    def inputs(self, trans, id, **kwd):
        """
        show( trans, id )
        * GET /api/jobs/{id}/inputs
            returns input datasets created by job

        :type   id: string
        :param  id: Encoded job id

        :rtype:     dictionary
        :returns:   dictionary containing input dataset associations
        """
        job = self.__get_job(trans, id)
        return self.__dictify_associations(trans, job.input_datasets, job.input_library_datasets)

    @expose_api
    def outputs(self, trans, id, **kwd):
        """
        show( trans, id )
        * GET /api/jobs/{id}/outputs
            returns output datasets created by job

        :type   id: string
        :param  id: Encoded job id

        :rtype:     dictionary
        :returns:   dictionary containing output dataset associations
        """
        job = self.__get_job(trans, id)
        return self.__dictify_associations(trans, job.output_datasets, job.output_library_datasets)

    @expose_api_anonymous
    def build_for_rerun(self, trans, id, **kwd):
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
            raise exceptions.ObjectNotFound("Could not access job with id '%s'" % id)
        tool = self.app.toolbox.get_tool(job.tool_id, kwd.get('tool_version') or job.tool_version)
        if tool is None:
            raise exceptions.ObjectNotFound("Requested tool not found")
        if not tool.is_workflow_compatible:
            raise exceptions.ConfigDoesNotAllowException("Tool '%s' cannot be rerun." % (job.tool_id))
        return tool.to_json(trans, {}, job=job)

    def __dictify_associations(self, trans, *association_lists):
        rval = []
        for association_list in association_lists:
            rval.extend(map(lambda a: self.__dictify_association(trans, a), association_list))
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

    def __get_job(self, trans, id):
        try:
            decoded_job_id = self.decode_id(id)
        except Exception:
            raise exceptions.MalformedId()
        job = trans.sa_session.query(trans.app.model.Job).filter(trans.app.model.Job.id == decoded_job_id).first()
        if job is None:
            raise exceptions.ObjectNotFound()
        if not trans.user_is_admin() and job.user != trans.user:
            if not job.output_datasets:
                raise exceptions.ItemAccessibilityException("Job has no output datasets.")
            for data_assoc in job.output_datasets:
                if not self.dataset_manager.is_accessible(data_assoc.dataset.dataset, trans.user):
                    raise exceptions.ItemAccessibilityException("You are not allowed to rerun this job.")
        return job

    @expose_api
    def create(self, trans, payload, **kwd):
        """ See the create method in tools.py in order to submit a job. """
        raise exceptions.NotImplemented('Please POST to /api/tools instead.')

    @expose_api
    def search(self, trans, payload, **kwd):
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

        tool_id = payload.get('tool_id')
        if tool_id is None:
            raise exceptions.ObjectAttributeMissingException("No tool id")

        tool = trans.app.toolbox.get_tool(tool_id)
        if tool is None:
            raise exceptions.ObjectNotFound("Requested tool not found")
        if 'inputs' not in payload:
            raise exceptions.ObjectAttributeMissingException("No inputs defined")

        inputs = payload['inputs']

        input_data = {}
        decoded_input_data = {}
        input_param = {}
        for k, v in inputs.items():
            if isinstance(v, dict):
                if 'id' in v:
                    decoded_id = self.decode_id(v['id'])
                    if 'src' not in v or v['src'] == 'hda':
                        dataset = self.hda_manager.get_accessible(decoded_id, trans.user)
                        datasets = trans.sa_session.query(model.HistoryDatasetAssociation).filter(model.HistoryDatasetAssociation.dataset_id == dataset.dataset_id).all()
                        hda_ids = decoded_ids = set(h.id for h in datasets)
                    else:
                        if v['src'] == 'hdca':
                            hdca = self.dataset_collection_manager.get_dataset_collection_instance(trans=trans,
                                                                                                   instance_type='history',
                                                                                                   id=v['id'],
                                                                                                   )
                            copied_from = getattr(hdca, 'copied_from_history_dataset_collection_association_id', None)
                            if hdca.deleted and not copied_from:
                                # We don't return the job if an input HDCA is marked as deleted -- it isn't necessary to be that strict,
                                # we could also just rely on the individual datasets to not be deleted.
                                return []
                            if copied_from:
                                # TODO: fetch these recursively or come up with a DB query to fetch all possible hdca ids
                                if hdca.deleted:
                                    hdca = trans.sa_session.query(model.HistoryDatasetCollectionAssociation).filter(
                                        model.HistoryDatasetCollectionAssociation.id == copied_from).first()
                                    if hdca.deleted:
                                        return []
                                decoded_ids = [decoded_id, copied_from]
                            else:
                                decoded_ids = [decoded_id]
                            datasets = hdca.dataset_instances
                            hda_ids = set(h.id for h in datasets)
                        else:
                            dataset = self.get_library_dataset_dataset_association(trans, v['id'])
                            hda_ids = decoded_ids = dataset.id
                    if datasets is None:
                        raise exceptions.ObjectNotFound("Dataset %s not found" % (v['id']))
                    parameter_values = []
                    for decoded_id in decoded_ids:
                        parameter_value = v.copy()
                        parameter_value['id'] = decoded_id
                        parameter_values.append(json.dumps({'values': [parameter_value]}))
                    decoded_input_data[k] = parameter_values
                    # We store the possible input hda ids keyed on input parameter if any of the
                    # corresponding HDAs exists
                    input_data[k] = hda_ids if any([d for d in datasets if not d.deleted]) else []
                    if not input_data[k]:
                        return []
            else:
                input_param[k] = json.dumps(str(v))

        query = trans.sa_session.query(model.Job).filter(
            model.Job.tool_id == tool_id,
            model.Job.user == trans.user
        )

        if 'state' not in payload:
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
            if isinstance(payload['state'], string_types):
                query = query.filter(model.Job.state == payload['state'])
            elif isinstance(payload['state'], list):
                o = []
                for s in payload['state']:
                    o.append(model.Job.state == s)
                query = query.filter(
                    or_(*o)
                )

        for k, v in input_param.items():
            a = aliased(model.JobParameter)
            query = query.filter(and_(
                model.Job.id == a.job_id,
                a.name == k,
                a.value == v
            ))

        for k, v in decoded_input_data.items():
            # Here we make sure that the incoming hdca/hda id
            # (v is a list of possible text representations of a input data parameter)
            # matches the right input data parameter for a job to be equivalent.
            # If we don't do this we return false positive jobs in case
            # a different combination of identical inputs has been used in a job.
            a = aliased(model.JobParameter)
            query = query.filter(and_(
                model.Job.id == a.job_id,
                a.name == k,
                a.value.in_(v)
            ))

        out = []
        for job in query.all():
            # check to make sure none of the output datasets or collections have been deleted
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
                out.append(self.encode_all_ids(trans, job.to_dict('element'), True))
        return out

    @expose_api
    def error(self, trans, id, **kwd):
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
        try:
            decoded_dataset_id = self.decode_id(kwd['dataset_id'])
        except Exception:
            raise exceptions.MalformedId()
        dataset = trans.sa_session.query(trans.app.model.HistoryDatasetAssociation).get(decoded_dataset_id)

        # Get job
        job = self.__get_job(trans, id)
        tool = trans.app.toolbox.get_tool(job.tool_id, tool_version=job.tool_version) or None
        messages = trans.app.error_reports.default_error_plugin.submit_report(
            dataset, job, tool, user_submission=True, user=trans.user,
            email=kwd.get('email', trans.user.email),
            message=kwd.get('message', None)
        )

        return {'messages': messages}
