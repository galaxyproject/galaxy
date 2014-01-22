"""
API operations on a jobs.

.. seealso:: :class:`galaxy.model.Jobs`
"""

import pkg_resources
pkg_resources.require( "Paste" )
from paste.httpexceptions import HTTPBadRequest, HTTPForbidden, HTTPInternalServerError, HTTPException

from sqlalchemy import or_

from galaxy import web
from galaxy.web import _future_expose_api as expose_api
from galaxy.web import _future_expose_api_anonymous as expose_api_anonymous
from galaxy.util import string_as_bool, restore_text
from galaxy.util.sanitize_html import sanitize_html
from galaxy.web.base.controller import BaseAPIController
from galaxy.web import url_for
from galaxy.model.orm import desc

import logging
log = logging.getLogger( __name__ )

class HistoriesController( BaseAPIController ):

    @web.expose_api
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

        state = kwd.get('state', None)
        query = trans.sa_session.query(trans.app.model.Job).filter( 
            trans.app.model.Job.user == trans.user )
        if state is not None:
            if isinstance(state, basestring):
                query = query.filter( trans.app.model.Job.state == state )
            elif isinstance(state, list):
                t = []
                for s in state:
                    t.append(  trans.app.model.Job.state == s )
                query = query.filter( or_( *t ) )

        out = []
        for job in query.order_by(
                trans.app.model.Job.update_time.desc()
            ).all():
            out.append( self.encode_all_ids( trans, job.to_dict('collection'), True) ) 
        return out

    @web.expose_api
    def show( self, trans, id, **kwd ):
        decoded_job_id = trans.security.decode_id(id)
        query = trans.sa_session.query(trans.app.model.Job).filter( 
            trans.app.model.Job.user == trans.user,
            trans.app.model.Job.id == decoded_job_id)
        job = query.first()
        if job is None:
            return None
        return self.encode_all_ids( trans, job.to_dict('element'), True)

    @expose_api
    def create( self, trans, payload, **kwd ):
        error = None
        if 'tool_id' not in payload:
            error = "No tool ID" 

        tool_id = payload.get('tool_id')

        if error is not None:
            return { "error" : error }


