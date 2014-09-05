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
from galaxy.web.base.controller import UsesHistoryMixin
from galaxy.web.base.controller import UsesTagsMixin
from galaxy.web.base.controller import ExportsHistoryMixin
from galaxy.web.base.controller import ImportsHistoryMixin

from galaxy.managers import histories, citations

from galaxy import util
from galaxy.util import string_as_bool
from galaxy.util import restore_text
from galaxy.web import url_for

import logging
log = logging.getLogger( __name__ )


class HistoriesController( BaseAPIController, UsesHistoryMixin, UsesTagsMixin,
                           ExportsHistoryMixin, ImportsHistoryMixin ):

    def __init__( self, app ):
        super( HistoriesController, self ).__init__( app )
        self.citations_manager = citations.CitationsManager( app )
        self.mgrs = util.bunch.Bunch(
            histories=histories.HistoryManager()
        )

    def _decode_id( self, trans, id ):
        try:
            return trans.security.decode_id( id )
        except:
            raise exceptions.MalformedId( "Malformed History id ( %s ) specified, unable to decode"
                                          % ( str( id ) ), type='error' )

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
        #TODO: query (by name, date, etc.)
        rval = []
        deleted = string_as_bool( deleted )

        histories = self.mgrs.histories.by_user( trans, user=trans.user, only_deleted=deleted )
        for history in histories:
            item = history.to_dict( value_mapper={ 'id': trans.security.encode_id } )
            item['url'] = url_for( 'history', id=trans.security.encode_id( history.id ) )
            rval.append( item )

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
        :returns:   detailed history information from
            :func:`galaxy.web.base.controller.UsesHistoryDatasetAssociationMixin.get_history_dict`
        """
        history_id = id
        deleted = string_as_bool( deleted )

        if history_id == "most_recently_used":
            if not trans.user or len( trans.user.galaxy_sessions ) <= 0:
                return None
            # Most recent active history for user sessions, not deleted
            history = trans.user.galaxy_sessions[0].histories[-1].history

        else:
            history = self.mgrs.histories.get( trans, self._decode_id( trans, history_id ),
                                               check_ownership=False, check_accessible=True, deleted=deleted )

        history_data = self.get_history_dict( trans, history )
        history_data[ 'contents_url' ] = url_for( 'history_contents', history_id=history_id )
        return history_data

    @expose_api_anonymous
    def citations( self, trans, history_id, **kwd ):
        history = self.mgrs.histories.get( trans, self._decode_id( trans, history_id ), check_ownership=False, check_accessible=True )
        tool_ids = set([])
        for dataset in history.datasets:
            job = dataset.creating_job
            if not job:
                continue
            tool_id = job.tool_id
            if not tool_id:
                continue
            tool_ids.add(tool_id)
        return map( lambda citation: citation.to_dict( "bibtex" ), self.citations_manager.citations_for_tool_ids( tool_ids ) )

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
            original_history = self.mgrs.histories.get( trans, self._decode_id( trans, copy_this_history_id ),
                check_ownership=False, check_accessible=True )
            hist_name = hist_name or ( "Copy of '%s'" % original_history.name )
            new_history = original_history.copy( name=hist_name, target_user=trans.user )

        # otherwise, create a new empty history
        else:
            new_history = trans.app.model.History( user=trans.user, name=hist_name )

        trans.sa_session.add( new_history )
        trans.sa_session.flush()

        item = {}
        item = self.get_history_dict( trans, new_history )
        item['url'] = url_for( 'history', id=item['id'] )
        return item

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

        rval = { 'id' : history_id }
        history = self.mgrs.histories.get( trans, self._decode_id( trans, history_id ),
            check_ownership=True, check_accessible=False )
        history.deleted = True
        if purge:
            if not trans.app.config.allow_user_dataset_purge and not trans.user_is_admin():
                raise exceptions.ConfigDoesNotAllowException( 'This instance does not allow user dataset purging' )

            # First purge all the datasets
            for hda in history.datasets:
                if hda.purged:
                    continue
                if hda.creating_job_associations:
                    job = hda.creating_job_associations[0].job
                    job.mark_deleted( self.app.config.track_jobs_in_database )
                    self.app.job_manager.job_stop_queue.put( job.id )
                hda.purged = True
                trans.sa_session.add( hda )
                trans.sa_session.flush()

                if hda.dataset.user_can_purge:
                    try:
                        hda.dataset.full_delete()
                        trans.sa_session.add( hda.dataset )
                    except:
                        pass
                    # flush now to preserve deleted state in case of later interruption
                    trans.sa_session.flush()

            # Now mark the history as purged
            history.purged = True
            self.sa_session.add( history )
            rval[ 'purged' ] = True

        trans.sa_session.flush()
        rval[ 'deleted' ] = True
        return rval

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
        history = self.mgrs.histories.get( trans, self._decode_id( trans, history_id ),
            check_ownership=True, check_accessible=False, deleted=True )
        history.deleted = False
        trans.sa_session.add( history )
        trans.sa_session.flush()
        return 'OK'

    @expose_api
    def update( self, trans, id, payload, **kwd ):
        """
        update( self, trans, id, payload, **kwd )
        * PUT /api/histories/{id}
            updates the values for the history with the given ``id``

        :type   id:      str
        :param  id:      the encoded id of the history to undelete
        :type   payload: dict
        :param  payload: a dictionary containing any or all the
            fields in :func:`galaxy.model.History.to_dict` and/or the following:

            * annotation: an annotation for the history

        :rtype:     dict
        :returns:   an error object if an error occurred or a dictionary containing
            any values that were different from the original and, therefore, updated
        """
        #TODO: PUT /api/histories/{encoded_history_id} payload = { rating: rating } (w/ no security checks)
        history_id = id

        history = self.mgrs.histories.get( trans, self._decode_id( trans, history_id ),
            check_ownership=True, check_accessible=True )
        # validation handled here and some parsing, processing, and conversion
        payload = self._validate_and_parse_update_payload( payload )
        # additional checks here (security, etc.)
        changed = self.set_history_from_dict( trans, history, payload )

        return changed

    @expose_api
    def archive_export( self, trans, id, **kwds ):
        """
        export_archive( self, trans, id, payload )
        * PUT /api/histories/{id}/exports:
            start job (if needed) to create history export for corresponding
            history.

        :type   id:     str
        :param  id:     the encoded id of the history to undelete

        :rtype:     dict
        :returns:   object containing url to fetch export from.
        """
        # PUT instead of POST because multiple requests should just result
        # in one object being created.
        history_id = id
        history = self.mgrs.histories.get( trans, self._decode_id( trans, history_id ),
            check_ownership=False, check_accessible=True )
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
        history_id = id
        history = self.mgrs.histories.get( trans, trans.security.decode_id( history_id ),
            check_ownership=False, check_accessible=True )
        matching_exports = filter( lambda e: trans.security.encode_id( e.id ) == jeha_id, history.exports )
        if not matching_exports:
            raise exceptions.ObjectNotFound()

        jeha = matching_exports[ 0 ]
        if not jeha.ready:
            # User should not have been given this URL, PUT export should have
            # return a 202.
            raise exceptions.MessageException( "Export not available or not yet ready." )

        return self.serve_ready_history_export( trans, jeha )

    def _validate_and_parse_update_payload( self, payload ):
        """
        Validate and parse incomming data payload for a history.
        """
        # This layer handles (most of the stricter idiot proofing):
        #   - unknown/unallowed keys
        #   - changing data keys from api key to attribute name
        #   - protection against bad data form/type
        #   - protection against malicious data content
        # all other conversions and processing (such as permissions, etc.) should happen down the line

        # keys listed here don't error when attempting to set, but fail silently
        #   this allows PUT'ing an entire model back to the server without attribute errors on uneditable attrs
        valid_but_uneditable_keys = (
            'id', 'model_class', 'nice_size', 'contents_url', 'purged', 'tags',
            'state', 'state_details', 'state_ids'
        )
        validated_payload = {}
        for key, val in payload.items():
            if val is None:
                continue
            if key in ( 'name', 'genome_build', 'annotation' ):
                validated_payload[ key ] = self.validate_and_sanitize_basestring( key, val )
            if key in ( 'deleted', 'published', 'importable' ):
                validated_payload[ key ] = self.validate_boolean( key, val )
            elif key == 'tags':
                validated_payload[ key ] = self.validate_and_sanitize_basestring_list( key, val )
            elif key not in valid_but_uneditable_keys:
                pass
                #log.warn( 'unknown key: %s', str( key ) )
        return validated_payload
