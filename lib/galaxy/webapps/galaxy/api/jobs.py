"""
API operations on a jobs.

.. seealso:: :class:`galaxy.model.Jobs`
"""

from sqlalchemy import or_, and_
from sqlalchemy.orm import aliased
import json
from galaxy.web import _future_expose_api as expose_api
from galaxy.web.base.controller import BaseAPIController
from galaxy.web.base.controller import UsesHistoryDatasetAssociationMixin
from galaxy.web.base.controller import UsesLibraryMixinItems
from galaxy import exceptions
from galaxy import util
from galaxy import model

import logging
log = logging.getLogger( __name__ )


class JobController( BaseAPIController, UsesHistoryDatasetAssociationMixin, UsesLibraryMixinItems ):

    @expose_api
    def index( self, trans, **kwd ):
        """
        index( trans, state=None, tool_id=None, history_id=None )
        * GET /api/jobs:
            return jobs for current user

        :type   state: string or list
        :param  state: limit listing of jobs to those that match one of the included states. If none, all are returned.
        Valid Galaxy job states include:
                'new', 'upload', 'waiting', 'queued', 'running', 'ok', 'error', 'paused', 'deleted', 'deleted_new'

        :type   tool_id: string or list
        :param  tool_id: limit listing of jobs to those that match one of the included tool_ids. If none, all are returned.

        :type   history_id: string
        :param  history_id: limit listing of jobs to those that match the history_id. If none, all are returned.

        :rtype:     list
        :returns:   list of dictionaries containing summary job information
        """

        state = kwd.get( 'state', None )
        query = trans.sa_session.query( trans.app.model.Job ).filter(
            trans.app.model.Job.user == trans.user
        )

        def build_and_apply_filters( query, objects, filter_func ):
            if objects is not None:
                if isinstance( objects, basestring ):
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

        history_id = kwd.get( 'history_id', None )
        if history_id is not None:
            try:
                decoded_history_id = trans.security.decode_id(history_id)
                query = query.filter( trans.app.model.Job.history_id == decoded_history_id )
            except:
                raise exceptions.ObjectAttributeInvalidException()

        out = []
        for job in query.order_by(
                trans.app.model.Job.update_time.desc()
            ).all():
            out.append( self.encode_all_ids( trans, job.to_dict( 'collection' ), True ) )
        return out

    @expose_api
    def show( self, trans, id, **kwd ):
        """
        show( trans, id )
        * GET /api/jobs/{job_id}:
            return jobs for current user

        :type   id: string
        :param  id: Specific job id

        :rtype:     dictionary
        :returns:   dictionary containing full description of job data
        """
        job = self.__get_job( trans, id )
        return self.encode_all_ids( trans, job.to_dict( 'element' ), True )

    @expose_api
    def inputs( self, trans, id, **kwd ):
        """
        show( trans, id )
        * GET /api/jobs/{job_id}/inputs
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
        * GET /api/jobs/{job_id}/outputs
            returns output datasets created by job

        :type   id: string
        :param  id: Encoded job id

        :rtype:     dictionary
        :returns:   dictionary containing output dataset associations
        """
        job = self.__get_job( trans, id )
        return self.__dictify_associations( trans, job.output_datasets, job.output_library_datasets )

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
            decoded_job_id = trans.security.decode_id( id )
        except Exception:
            raise exceptions.MalformedId()
        query = trans.sa_session.query( trans.app.model.Job ).filter(
            trans.app.model.Job.user == trans.user,
            trans.app.model.Job.id == decoded_job_id
        )
        job = query.first()
        if job is None:
            raise exceptions.ObjectNotFound()
        return job

    @expose_api
    def create( self, trans, payload, **kwd ):
        raise NotImplementedError()

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
                        dataset = self.get_dataset( trans, v['id'], check_ownership=False, check_accessible=True )
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
            if isinstance( payload[ 'state' ], basestring ):
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
            """
            Here we are attempting to link the inputs to the underlying dataset (not the dataset association)
            This way, if the calulation was done using a copied HDA (copied from the library or another history)
            the search will still find the job
            """
            a = aliased( trans.app.model.JobToInputDatasetAssociation )
            b = aliased( trans.app.model.HistoryDatasetAssociation )
            query = query.filter( and_(
                trans.app.model.Job.id == a.job_id,
                a.dataset_id == b.id,
                b.deleted == False,
                b.dataset_id == v
            ) )

        out = []
        for job in query.all():
            """
            check to make sure none of the output files have been deleted
            """
            if all( list( a.dataset.deleted == False for a in job.output_datasets ) ):
                out.append( self.encode_all_ids( trans, job.to_dict( 'element' ), True ) )
        return out
