"""
API operations on a jobs.

.. seealso:: :class:`galaxy.model.Jobs`
"""

import logging

from six import string_types
from sqlalchemy import or_

from galaxy import exceptions
from galaxy import model
from galaxy import util
from galaxy.managers.datasets import DatasetManager
from galaxy.managers.jobs import JobSearch
from galaxy.web import _future_expose_api as expose_api
from galaxy.web import _future_expose_api_anonymous as expose_api_anonymous
from galaxy.web.base.controller import BaseAPIController
from galaxy.web.base.controller import UsesLibraryMixinItems
from galaxy.work.context import WorkRequestContext

log = logging.getLogger(__name__)


class JobController(BaseAPIController, UsesLibraryMixinItems):

    def __init__(self, app):
        super(JobController, self).__init__(app)
        self.dataset_manager = DatasetManager(app)
        self.job_search = JobSearch(app)

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
        is_admin = trans.user_is_admin
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
            except Exception:
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

    @expose_api_anonymous
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
        is_admin = trans.user_is_admin
        job_dict = self.encode_all_ids(trans, job.to_dict('element', system_details=is_admin), True)
        full_output = util.asbool(kwd.get('full', 'false'))
        if full_output:
            job_dict.update(dict(stderr=job.stderr, stdout=job.stdout))
            if is_admin:
                if job.user:
                    job_dict['user_email'] = job.user.email
                else:
                    job_dict['user_email'] = None

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
    def delete(self, trans, id, **kwd):
        """
        delete( trans, id )
        * Delete /api/jobs/{id}
            cancels specified job

        :type   id: string
        :param  id: Encoded job id
        """
        job = self.__get_job(trans, id)
        if not job.finished:
            job.mark_deleted(self.app.config.track_jobs_in_database)
            trans.sa_session.flush()
            self.app.job_manager.stop(job)
            return True
        else:
            return False

    @expose_api
    def resume(self, trans, id, **kwd):
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
            raise exceptions.ObjectNotFound("Could not access job with id '%s'" % id)
        if job.state == job.states.PAUSED:
            job.resume()
        else:
            exceptions.RequestParameterInvalidException("Job with id '%s' is not paused" % (job.tool_id))
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

    def __get_job(self, trans, id):
        try:
            decoded_job_id = self.decode_id(id)
        except Exception:
            raise exceptions.MalformedId()
        job = trans.sa_session.query(trans.app.model.Job).filter(trans.app.model.Job.id == decoded_job_id).first()
        if job is None:
            raise exceptions.ObjectNotFound()
        belongs_to_user = (job.user == trans.user) if job.user else (job.session_id == trans.get_galaxy_session().id)
        if not trans.user_is_admin and not belongs_to_user:
            # Check access granted via output datasets.
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
        inputs = payload.get('inputs', {})
        # Find files coming in as multipart file data and add to inputs.
        for k, v in payload.items():
            if k.startswith('files_') or k.startswith('__files_'):
                inputs[k] = v
        request_context = WorkRequestContext(app=trans.app, user=trans.user, history=trans.history)
        all_params, all_errors, _, _ = tool.expand_incoming(trans=trans, incoming=inputs, request_context=request_context)
        if any(all_errors):
            return []
        params_dump = [tool.params_to_strings(param, self.app, nested=True) for param in all_params]
        jobs = []
        for param_dump, param in zip(params_dump, all_params):
            job = self.job_search.by_tool_input(trans=trans,
                                                tool_id=tool_id,
                                                tool_version=tool.version,
                                                param=param,
                                                param_dump=param_dump,
                                                job_state=payload.get('state'))
            if job:
                jobs.append(job)
        return [self.encode_all_ids(trans, single_job.to_dict('element'), True) for single_job in jobs]

    @expose_api_anonymous
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
        email = kwd.get('email')
        if not email and not trans.anonymous:
            email = trans.user.email
        messages = trans.app.error_reports.default_error_plugin.submit_report(
            dataset=dataset,
            job=job,
            tool=tool,
            user_submission=True,
            user=trans.user,
            email=email,
            message=kwd.get('message')
        )

        return {'messages': messages}
