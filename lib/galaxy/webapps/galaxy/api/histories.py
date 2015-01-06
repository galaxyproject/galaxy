"""
API operations on a history.

.. seealso:: :class:`galaxy.model.History`
"""

import pkg_resources
pkg_resources.require( "Paste" )

from galaxy import exceptions
from galaxy.web import _future_expose_api as expose_api
from galaxy.web import _future_expose_api_anonymous as expose_api_anonymous
from galaxy.web import _future_expose_api_raw as expose_api_raw

from galaxy.web.base.controller import BaseAPIController
from galaxy.web.base.controller import ExportsHistoryMixin
from galaxy.web.base.controller import ImportsHistoryMixin

from galaxy.managers import histories, citations

from galaxy import util
from galaxy.util import string_as_bool
from galaxy.util import restore_text
from galaxy.web import url_for

import logging
log = logging.getLogger( __name__ )


class HistoriesController( BaseAPIController, ExportsHistoryMixin, ImportsHistoryMixin ):

    def __init__( self, app ):
        super( HistoriesController, self ).__init__( app )
        self.citations_manager = citations.CitationsManager( app )
        self.mgrs = util.bunch.Bunch(
            histories=histories.HistoryManager( app )
        )
        self.history_serializer = histories.HistorySerializer( app )
        self.history_deserializer = histories.HistoryDeserializer( app )

    def _decode_id( self, trans, id ):
        try:
            return trans.security.decode_id( id )
        except:
            raise exceptions.MalformedId( "Malformed History id ( %s ) specified, unable to decode"
                                          % ( str( id ) ), type='error' )

    def _parse_serialization_params( self, kwd, default_view ):
        view = kwd.get( 'view', None )
        keys = kwd.get( 'keys' )
        if isinstance( keys, basestring ):
            keys = keys.split( ',' )
        return dict( view=view, keys=keys, default_view=default_view )

    @expose_api_anonymous
    def index( self, trans, deleted='False', **kwd ):
        """
        index( trans, deleted='False' )
        * GET /api/histories:
            return undeleted histories for the current user
        * GET /api/histories/deleted:
            return deleted histories for the current user
        .. note:: Anonymous users are allowed to get their current history

        :type   deleted: boolean
        :param  deleted: if True, show only deleted histories, if False, non-deleted

        :rtype:     list
        :returns:   list of dictionaries containing summary history information
        """
        rval = []
        serialization_params = self._parse_serialization_params( kwd, 'summary' )

        deleted_filter = ( self.app.model.History.deleted == False )
        if string_as_bool( deleted ):
            deleted_filter = ( self.app.model.History.deleted == True )

        histories = self.mgrs.histories.by_user( trans, user=trans.user, filters=deleted_filter )
        for history in histories:
            history_dict = self.history_serializer.serialize_to_view( trans, history, **serialization_params )
            rval.append( history_dict )

        return rval

    @expose_api_anonymous
    def show( self, trans, id, deleted='False', **kwd ):
        """
        show( trans, id, deleted='False' )
        * GET /api/histories/{id}:
            return the history with ``id``
        * GET /api/histories/deleted/{id}:
            return the deleted history with ``id``
        * GET /api/histories/most_recently_used:
            return the most recently used history

        :type   id:      an encoded id string
        :param  id:      the encoded id of the history to query or the string 'most_recently_used'
        :type   deleted: boolean
        :param  deleted: if True, allow information on a deleted history to be shown.

        :rtype:     dictionary
        :returns:   detailed history information
        """
        history_id = id
        deleted = string_as_bool( deleted )

        if history_id == "most_recently_used":
            history = self.mgrs.histories.most_recent( trans, trans.user,
                filters=( self.app.model.History.deleted == False ) )
        else:
            history = self.mgrs.histories.accessible_by_id( trans, self._decode_id( trans, history_id ), trans.user )

        return self.history_serializer.serialize_to_view( trans, history,
            **self._parse_serialization_params( kwd, 'detailed' ) )

    @expose_api_anonymous
    def citations( self, trans, history_id, **kwd ):
        """
        """
        history = self.mgrs.histories.accessible_by_id( trans, self._decode_id( trans, history_id ), trans.user )
        tool_ids = set([])
        for dataset in history.datasets:
            job = dataset.creating_job
            if not job:
                continue
            tool_id = job.tool_id
            if not tool_id:
                continue
            tool_ids.add(tool_id)
        return map( lambda citation: citation.to_dict( "bibtex" ),
                    self.citations_manager.citations_for_tool_ids( tool_ids ) )

    @expose_api
    def create( self, trans, payload, **kwd ):
        """
        create( trans, payload )
        * POST /api/histories:
            create a new history

        :type   payload: dict
        :param  payload: (optional) dictionary structure containing:
            * name:             the new history's name
            * history_id:       the id of the history to copy
            * archive_source:   the url that will generate the archive to import
            * archive_type:     'url' (default)

        :rtype:     dict
        :returns:   element view of new history
        """
        hist_name = None
        if payload.get( 'name', None ):
            hist_name = restore_text( payload['name'] )
        copy_this_history_id = payload.get( 'history_id', None )

        if "archive_source" in payload:
            archive_source = payload[ "archive_source" ]
            archive_type = payload.get( "archive_type", "url" )
            self.queue_history_import( trans, archive_type=archive_type, archive_source=archive_source )
            return {}

        new_history = None
        # if a history id was passed, copy that history
        if copy_this_history_id:
            decoded_id = self._decode_id( trans, copy_this_history_id )
            original_history = self.mgrs.histories.accessible_by_id( trans, decoded_id, trans.user )
            hist_name = hist_name or ( "Copy of '%s'" % original_history.name )
            new_history = original_history.copy( name=hist_name, target_user=trans.user )

        # otherwise, create a new empty history
        else:
            new_history = trans.app.model.History( user=trans.user, name=hist_name )

        trans.sa_session.add( new_history )
        trans.sa_session.flush()

        return self.history_serializer.serialize_to_view( trans, new_history,
            **self._parse_serialization_params( kwd, 'detailed' ) )

    @expose_api
    def delete( self, trans, id, **kwd ):
        """
        delete( self, trans, id, **kwd )
        * DELETE /api/histories/{id}
            delete the history with the given ``id``
        .. note:: Stops all active jobs in the history if purge is set.

        :type   id:     str
        :param  id:     the encoded id of the history to delete
        :type   kwd:    dict
        :param  kwd:    (optional) dictionary structure containing:

            * payload:     a dictionary itself containing:
                * purge:   if True, purge the history and all of its HDAs

        :rtype:     dict
        :returns:   an error object if an error occurred or a dictionary containing:
            * id:         the encoded id of the history,
            * deleted:    if the history was marked as deleted,
            * purged:     if the history was purged
        """
        history_id = id
        # a request body is optional here
        purge = False
        if kwd.get( 'payload', None ):
            purge = string_as_bool( kwd['payload'].get( 'purge', False ) )

        history = self.mgrs.histories.owned_by_id( trans, self._decode_id( trans, history_id ), trans.user )
        self.mgrs.histories.delete( trans, history )
        if purge:
            self.mgrs.histories.purge( trans, history )

        return self.history_serializer.serialize_to_view( trans, new_history,
            **self._parse_serialization_params( kwd, 'detailed' ) )

    @expose_api
    def undelete( self, trans, id, **kwd ):
        """
        undelete( self, trans, id, **kwd )
        * POST /api/histories/deleted/{id}/undelete:
            undelete history (that hasn't been purged) with the given ``id``

        :type   id:     str
        :param  id:     the encoded id of the history to undelete

        :rtype:     str
        :returns:   'OK' if the history was undeleted
        """
        history_id = id
        history = self.mgrs.histories.owned_by_id( trans, self._decode_id( trans, history_id ), trans.user )
        self.mgrs.histories.undelete( trans, history )

        return self.history_serializer.serialize_to_view( trans, history,
            **self._parse_serialization_params( kwd, 'detailed' ) )

    @expose_api
    def update( self, trans, id, payload, **kwd ):
        """
        update( self, trans, id, payload, **kwd )
        * PUT /api/histories/{id}
            updates the values for the history with the given ``id``

        :type   id:      str
        :param  id:      the encoded id of the history to update
        :type   payload: dict
        :param  payload: a dictionary containing any or all the
            fields in :func:`galaxy.model.History.to_dict` and/or the following:

            * annotation: an annotation for the history

        :rtype:     dict
        :returns:   an error object if an error occurred or a dictionary containing
            any values that were different from the original and, therefore, updated
        """
        #TODO: PUT /api/histories/{encoded_history_id} payload = { rating: rating } (w/ no security checks)
        history = self.mgrs.histories.owned_by_id( trans, self._decode_id( trans, id ), trans.user )

        #TODO: flushing in deserialize is an iffy pattern...
        self.history_deserializer.deserialize( trans, history, payload )
        return self.history_serializer.serialize_to_view( trans, history,
            **self._parse_serialization_params( kwd, 'detailed' ) )

    @expose_api
    def archive_export( self, trans, id, **kwds ):
        """
        export_archive( self, trans, id, payload )
        * PUT /api/histories/{id}/exports:
            start job (if needed) to create history export for corresponding
            history.

        :type   id:     str
        :param  id:     the encoded id of the history to export

        :rtype:     dict
        :returns:   object containing url to fetch export from.
        """
        # PUT instead of POST because multiple requests should just result
        # in one object being created.
        history = self.mgrs.histories.accessible_by_id( trans, self._decode_id( trans, id ), trans.user )
        jeha = history.latest_export
        up_to_date = jeha and jeha.up_to_date
        if 'force' in kwds:
            up_to_date = False #Temp hack to force rebuild everytime during dev
        if not up_to_date:
            # Need to create new JEHA + job.
            gzip = kwds.get( "gzip", True )
            include_hidden = kwds.get( "include_hidden", False )
            include_deleted = kwds.get( "include_deleted", False )
            self.queue_history_export( trans, history, gzip=gzip, include_hidden=include_hidden, include_deleted=include_deleted )

        if up_to_date and jeha.ready:
            jeha_id = trans.security.encode_id( jeha.id )
            return dict( download_url=url_for( "history_archive_download", id=id, jeha_id=jeha_id ) )
        else:
            # Valid request, just resource is not ready yet.
            trans.response.status = "202 Accepted"
            return ''

    @expose_api_raw
    def archive_download( self, trans, id, jeha_id, **kwds ):
        """
        export_download( self, trans, id, jeha_id )
        * GET /api/histories/{id}/exports/{jeha_id}:
            If ready and available, return raw contents of exported history.
            Use/poll "PUT /api/histories/{id}/exports" to initiate the creation
            of such an export - when ready that route will return 200 status
            code (instead of 202) with a JSON dictionary containing a
            `download_url`.
        """
        # Seems silly to put jeha_id in here, but want GET to be immuatable?
        # and this is being accomplished this way.
        history = self.mgrs.histories.accessible_by_id( trans, self._decode_id( trans, id ), trans.user )
        matching_exports = filter( lambda e: trans.security.encode_id( e.id ) == jeha_id, history.exports )
        if not matching_exports:
            raise exceptions.ObjectNotFound()

        jeha = matching_exports[ 0 ]
        if not jeha.ready:
            # User should not have been given this URL, PUT export should have
            # return a 202.
            raise exceptions.MessageException( "Export not available or not yet ready." )

        return self.serve_ready_history_export( trans, jeha )
