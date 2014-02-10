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

import logging
log = logging.getLogger( __name__ )


class JobController( BaseAPIController, UsesHistoryDatasetAssociationMixin, UsesLibraryMixinItems ):

    @expose_api
    def index( self, trans, **kwd ):
        """
        index( trans, state=None )
        * GET /api/jobs:
            return jobs for current user

        :type   state: string or list
        :param  state: limit listing of jobs to those that match one of the included states. If none, all are returned.
        Valid Galaxy job states include:
                'new', 'upload', 'waiting', 'queued', 'running', 'ok', 'error', 'paused', 'deleted', 'deleted_new'

        :rtype:     list
        :returns:   list of dictionaries containing summary job information
        """

        state = kwd.get( 'state', None )
        query = trans.sa_session.query( trans.app.model.Job ).filter(
            trans.app.model.Job.user == trans.user
        )
        if state is not None:
            if isinstance( state, basestring ):
                query = query.filter( trans.app.model.Job.state == state )
            elif isinstance( state, list ):
                t = []
                for s in state:
                    t.append(  trans.app.model.Job.state == s )
                query = query.filter( or_( *t ) )

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
        try:
            decoded_job_id = trans.security.decode_id(id)
        except:
            raise exceptions.ObjectAttributeInvalidException()
        query = trans.sa_session.query( trans.app.model.Job ).filter(
            trans.app.model.Job.user == trans.user,
            trans.app.model.Job.id == decoded_job_id
        )
        job = query.first()
        if job is None:
            raise exceptions.ObjectNotFound()
        return self.encode_all_ids( trans, job.to_dict( 'element' ), True )

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
