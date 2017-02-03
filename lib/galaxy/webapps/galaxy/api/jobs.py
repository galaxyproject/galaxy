"""
API operations on a jobs.

.. seealso:: :class:`galaxy.model.Jobs`
"""

import json
import logging

from six import string_types
from sqlalchemy import and_, false, or_
from sqlalchemy.orm import aliased

from galaxy import exceptions
from galaxy import managers
from galaxy import model
from galaxy import util
from galaxy.web import _future_expose_api as expose_api
from galaxy.web import _future_expose_api_anonymous as expose_api_anonymous
from galaxy.web.base.controller import BaseAPIController
from galaxy.web.base.controller import UsesLibraryMixinItems

log = logging.getLogger( __name__ )


class JobController( BaseAPIController, UsesLibraryMixinItems ):

    def __init__( self, app ):
        super( JobController, self ).__init__( app )
        self.hda_manager = managers.hdas.HDAManager( app )
        self.dataset_manager = managers.datasets.DatasetManager( app )

    @expose_api
    def index( self, trans, **kwd ):
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
        state = kwd.get( 'state', None )
        is_admin = trans.user_is_admin()
        user_details = kwd.get('user_details', False)

        if is_admin:
            query = trans.sa_session.query( trans.app.model.Job )
        else:
            query = trans.sa_session.query( trans.app.model.Job ).filter(trans.app.model.Job.user == trans.user)

        def build_and_apply_filters( query, objects, filter_func ):
            if objects is not None:
                if isinstance( objects, string_types ):
                    query = query.filter( filter_func( objects ) )
                elif isinstance( objects, list ):
                    t = []
                    for obj in objects:
                        t.append( filter_func( obj ) )
                    query = query.filter( or_( *t ) )
            return query

        query = build_and_apply_filters( query, state, lambda s: trans.app.model.Job.state == s )

        query = build_and_apply_filters( query, kwd.get( 'tool_id', None ), lambda t: trans.app.model.Job.tool_id == t )
        query = build_and_apply_filters( query, kwd.get( 'tool_id_like', None ), lambda t: trans.app.model.Job.tool_id.like(t) )

        query = build_and_apply_filters( query, kwd.get( 'date_range_min', None ), lambda dmin: trans.app.model.Job.table.c.update_time >= dmin )
        query = build_and_apply_filters( query, kwd.get( 'date_range_max', None ), lambda dmax: trans.app.model.Job.table.c.update_time <= dmax )

        history_id = kwd.get( 'history_id', None )
        if history_id is not None:
            try:
                decoded_history_id = self.decode_id(history_id)
                query = query.filter( trans.app.model.Job.history_id == decoded_history_id )
            except:
                raise exceptions.ObjectAttributeInvalidException()

        out = []
        if kwd.get( 'order_by' ) == 'create_time':
            order_by = trans.app.model.Job.create_time.desc()
        else:
            order_by = trans.app.model.Job.update_time.desc()
        for job in query.order_by( order_by ).all():
            job_dict = job.to_dict( 'collection', system_details=is_admin )
            j = self.encode_all_ids( trans, job_dict, True )
            if user_details:
                j['user_email'] = job.user.email
            out.append(j)

        return out

    @expose_api
    def show( self, trans, id, **kwd ):
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
        job = self.__get_job( trans, id )
        is_admin = trans.user_is_admin()
        job_dict = self.encode_all_ids( trans, job.to_dict( 'element', system_details=is_admin ), True )
        full_output = util.asbool( kwd.get( 'full', 'false' ) )
        if full_output:
            job_dict.update( dict( stderr=job.stderr, stdout=job.stdout ) )
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
    def inputs( self, trans, id, **kwd ):
        """
        show( trans, id )
        * GET /api/jobs/{id}/inputs
            returns input datasets created by job

        :type   id: string
        :param  id: Encoded job id

        :rtype:     dictionary
        :returns:   dictionary containing input dataset associations
        """
        job = self.__get_job( trans, id )
        return self.__dictify_associations( trans, job.input_datasets, job.input_library_datasets )

    @expose_api
    def outputs( self, trans, id, **kwd ):
        """
        show( trans, id )
        * GET /api/jobs/{id}/outputs
            returns output datasets created by job

        :type   id: string
        :param  id: Encoded job id

        :rtype:     dictionary
        :returns:   dictionary containing output dataset associations
        """
        job = self.__get_job( trans, id )
        return self.__dictify_associations( trans, job.output_datasets, job.output_library_datasets )

    @expose_api_anonymous
    def build_for_rerun( self, trans, id, **kwd ):
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
        tool = self.app.toolbox.get_tool( job.tool_id, job.tool_version )
        if tool is None:
            raise exceptions.ObjectNotFound( "Requested tool not found" )
        if not tool.is_workflow_compatible:
            raise exceptions.ConfigDoesNotAllowException( "Tool '%s' cannot be rerun." % ( job.tool_id ) )
        return tool.to_json(trans, {}, job=job)

    def __dictify_associations( self, trans, *association_lists ):
        rval = []
        for association_list in association_lists:
            rval.extend( map( lambda a: self.__dictify_association( trans, a ), association_list ) )
        return rval

    def __dictify_association( self, trans, job_dataset_association ):
        dataset_dict = None
        dataset = job_dataset_association.dataset
        if dataset:
            if isinstance( dataset, model.HistoryDatasetAssociation ):
                dataset_dict = dict( src="hda", id=trans.security.encode_id( dataset.id ) )
            else:
                dataset_dict = dict( src="ldda", id=trans.security.encode_id( dataset.id ) )
        return dict( name=job_dataset_association.name, dataset=dataset_dict )

    def __get_job( self, trans, id ):
        try:
            decoded_job_id = self.decode_id( id )
        except Exception:
            raise exceptions.MalformedId()
        job = trans.sa_session.query( trans.app.model.Job ).filter( trans.app.model.Job.id == decoded_job_id ).first()
        if job is None:
            raise exceptions.ObjectNotFound()
        if not trans.user_is_admin() and job.user != trans.user:
            if not job.output_datasets:
                raise exceptions.ItemAccessibilityException( "Job has no output datasets." )
            for data_assoc in job.output_datasets:
                if not self.dataset_manager.is_accessible( data_assoc.dataset.dataset, trans.user ):
                    raise exceptions.ItemAccessibilityException( "You are not allowed to rerun this job." )
        return job

    @expose_api
    def create( self, trans, payload, **kwd ):
        """ See the create method in tools.py in order to submit a job. """
        raise exceptions.NotImplemented( 'Please POST to /api/tools instead.' )

    @expose_api
    def search( self, trans, payload, **kwd ):
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

        tool_id = None
        if 'tool_id' in payload:
            tool_id = payload.get( 'tool_id' )
        if tool_id is None:
            raise exceptions.ObjectAttributeMissingException( "No tool id" )

        tool = trans.app.toolbox.get_tool( tool_id )
        if tool is None:
            raise exceptions.ObjectNotFound( "Requested tool not found" )
        if 'inputs' not in payload:
            raise exceptions.ObjectAttributeMissingException( "No inputs defined" )

        inputs = payload[ 'inputs' ]

        input_data = {}
        input_param = {}
        for k, v in inputs.items():
            if isinstance( v, dict ):
                if 'id' in v:
                    if 'src' not in v or v[ 'src' ] == 'hda':
                        hda_id = self.decode_id( v['id'] )
                        dataset = self.hda_manager.get_accessible( hda_id, trans.user )
                    else:
                        dataset = self.get_library_dataset_dataset_association( trans, v['id'] )
                    if dataset is None:
                        raise exceptions.ObjectNotFound( "Dataset %s not found" % ( v[ 'id' ] ) )
                    input_data[k] = dataset.dataset_id
            else:
                input_param[k] = json.dumps( str(v) )

        query = trans.sa_session.query( trans.app.model.Job ).filter(
            trans.app.model.Job.tool_id == tool_id,
            trans.app.model.Job.user == trans.user
        )

        if 'state' not in payload:
            query = query.filter(
                or_(
                    trans.app.model.Job.state == 'running',
                    trans.app.model.Job.state == 'queued',
                    trans.app.model.Job.state == 'waiting',
                    trans.app.model.Job.state == 'running',
                    trans.app.model.Job.state == 'ok',
                )
            )
        else:
            if isinstance( payload[ 'state' ], string_types ):
                query = query.filter( trans.app.model.Job.state == payload[ 'state' ] )
            elif isinstance( payload[ 'state' ], list ):
                o = []
                for s in payload[ 'state' ]:
                    o.append( trans.app.model.Job.state == s )
                query = query.filter(
                    or_( *o )
                )

        for k, v in input_param.items():
            a = aliased( trans.app.model.JobParameter )
            query = query.filter( and_(
                trans.app.model.Job.id == a.job_id,
                a.name == k,
                a.value == v
            ) )

        for k, v in input_data.items():
            # Here we are attempting to link the inputs to the underlying
            # dataset (not the dataset association).
            # This way, if the calculation was done using a copied HDA
            # (copied from the library or another history), the search will
            # still find the job
            a = aliased( trans.app.model.JobToInputDatasetAssociation )
            b = aliased( trans.app.model.HistoryDatasetAssociation )
            query = query.filter( and_(
                trans.app.model.Job.id == a.job_id,
                a.dataset_id == b.id,
                b.deleted == false(),
                b.dataset_id == v
            ) )

        out = []
        for job in query.all():
            # check to make sure none of the output files have been deleted
            if all( list( a.dataset.deleted is False for a in job.output_datasets ) ):
                out.append( self.encode_all_ids( trans, job.to_dict( 'element' ), True ) )
        return out
