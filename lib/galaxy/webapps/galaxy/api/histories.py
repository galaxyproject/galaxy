"""
API operations on a history.

.. seealso:: :class:`galaxy.model.History`
"""

import pkg_resources
pkg_resources.require( "Paste" )
from paste.httpexceptions import HTTPBadRequest, HTTPForbidden, HTTPInternalServerError, HTTPException

from galaxy import web
from galaxy.web import _future_expose_api as expose_api
from galaxy.web import _future_expose_api_anonymous as expose_api_anonymous
from galaxy.util import string_as_bool
from galaxy.util import restore_text
from galaxy.web.base.controller import BaseAPIController
from galaxy.web.base.controller import UsesHistoryMixin
from galaxy.web.base.controller import UsesTagsMixin
from galaxy.web import url_for

import logging
log = logging.getLogger( __name__ )


class HistoriesController( BaseAPIController, UsesHistoryMixin, UsesTagsMixin ):

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
        try:
            if trans.user:
                histories = self.get_user_histories( trans, user=trans.user, only_deleted=deleted )
                #for history in query:
                for history in histories:
                    item = history.to_dict(value_mapper={'id': trans.security.encode_id})
                    item['url'] = url_for( 'history', id=trans.security.encode_id( history.id ) )
                    rval.append( item )

            elif trans.galaxy_session.current_history:
                #No user, this must be session authentication with an anonymous user.
                history = trans.galaxy_session.current_history
                item = history.to_dict(value_mapper={'id': trans.security.encode_id})
                item['url'] = url_for( 'history', id=trans.security.encode_id( history.id ) )
                rval.append(item)

        except Exception, e:
            raise
            rval = "Error in history API"
            log.error( rval + ": %s" % str(e) )
            trans.response.status = 500
        return rval

    @web.expose_api_anonymous
    def show( self, trans, id, deleted='False', **kwd ):
        """
        show( trans, id, deleted='False' )
        * GET /api/histories/{id}:
            return the history with ``id``
        * GET /api/histories/deleted/{id}:
            return the deleted history with ``id``
        * GET /api/histories/most_recently_used:
            return the most recently used history
        .. note:: Anonymous users are allowed to get their current history

        :type   id:      an encoded id string
        :param  id:      the encoded id of the history to query or the string 'most_recently_used'
        :type   deleted: boolean
        :param  deleted: if True, allow information on a deleted history to be shown.

        :rtype:     dictionary
        :returns:   detailed history information from
            :func:`galaxy.web.base.controller.UsesHistoryDatasetAssociationMixin.get_history_dict`
        """
        #TODO: GET /api/histories/{encoded_history_id}?as_archive=True
        #TODO: GET /api/histories/s/{username}/{slug}
        history_id = id
        deleted = string_as_bool( deleted )

        try:
            if history_id == "most_recently_used":
                if not trans.user or len( trans.user.galaxy_sessions ) <= 0:
                    return None
                # Most recent active history for user sessions, not deleted
                history = trans.user.galaxy_sessions[0].histories[-1].history

            elif history_id == "current":
                history = trans.get_history( create=True )

            else:
                history = self.get_history( trans, history_id, check_ownership=False,
                                            check_accessible=True, deleted=deleted )

            history_data = self.get_history_dict( trans, history )
            history_data[ 'contents_url' ] = url_for( 'history_contents', history_id=history_id )

        except HTTPBadRequest, bad_req:
            trans.response.status = 400
            return str( bad_req )

        except Exception, e:
            msg = "Error in history API at showing history detail: %s" % ( str( e ) )
            log.exception( msg )
            trans.response.status = 500
            return msg

        return history_data

    @web.expose_api
    def set_as_current( self, trans, id, **kwd ):
        """
        set_as_current( trans, id, **kwd )
        * POST /api/histories/{id}/set_as_current:
            set the history with ``id`` to the user's current history and return details

        :type   id:      an encoded id string
        :param  id:      the encoded id of the history to query or the string 'most_recently_used'

        :rtype:     dictionary
        :returns:   detailed history information from
            :func:`galaxy.web.base.controller.UsesHistoryDatasetAssociationMixin.get_history_dict`
        """
        # added as a non-ATOM API call to support the notion of a 'current/working' history
        #   - unique to the history resource
        history_id = id
        try:
            history = self.get_history( trans, history_id, check_ownership=True, check_accessible=True )
            trans.history = history
            history_data = self.get_history_dict( trans, history )
            history_data[ 'contents_url' ] = url_for( 'history_contents', history_id=history_id )

        except HTTPBadRequest, bad_req:
            trans.response.status = 400
            return str( bad_req )

        except Exception, e:
            msg = "Error in history API when switching current history: %s" % ( str( e ) )
            log.exception( msg )
            trans.response.status = 500
            return msg

        return history_data

    @expose_api
    def create( self, trans, payload, **kwd ):
        """
        create( trans, payload )
        * POST /api/histories:
            create a new history

        :type   payload: dict
        :param  payload: (optional) dictionary structure containing:
            * name:     the new history's name
            * current:  if passed, set the new history to be the user's 'current'
                        history

        :rtype:     dict
        :returns:   element view of new history
        """
        hist_name = None
        if payload.get( 'name', None ):
            hist_name = restore_text( payload['name'] )
        new_history = trans.app.model.History( user=trans.user, name=hist_name )

        trans.sa_session.add( new_history )
        trans.sa_session.flush()
        #item = new_history.to_dict(view='element', value_mapper={'id':trans.security.encode_id})
        item = self.get_history_dict( trans, new_history )
        item['url'] = url_for( 'history', id=item['id'] )

        #TODO: possibly default to True here - but favor explicit for now (and backwards compat)
        current = string_as_bool( payload[ 'current' ] ) if 'current' in payload else False
        if current:
            trans.history = new_history

        #TODO: copy own history
        #TODO: import an importable history
        #TODO: import from archive
        return item

    @web.expose_api
    def delete( self, trans, id, **kwd ):
        """
        delete( self, trans, id, **kwd )
        * DELETE /api/histories/{id}
            delete the history with the given ``id``
        .. note:: Currently does not stop any active jobs in the history.

        :type   id:     str
        :param  id:     the encoded id of the history to delete
        :type   kwd:    dict
        :param  kwd:    (optional) dictionary structure containing:

            * payload:     a dictionary itself containing:
                * purge:   if True, purge the history and all of it's HDAs

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
        try:
            history = self.get_history( trans, history_id, check_ownership=True, check_accessible=False )
            history.deleted = True

            if purge:
                if not trans.app.config.allow_user_dataset_purge:
                    raise HTTPForbidden( detail='This instance does not allow user dataset purging' )

                # First purge all the datasets
                for hda in history.datasets:
                    if hda.purged:
                        continue
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

        except HTTPInternalServerError, http_server_err:
            log.exception( 'Histories API, delete: uncaught HTTPInternalServerError: %s, %s\n%s',
                           history_id, str( kwd ), str( http_server_err ) )
            raise
        except HTTPException:
            raise
        except Exception, exc:
            log.exception( 'Histories API, delete: uncaught exception: %s, %s\n%s',
                           history_id, str( kwd ), str( exc ) )
            trans.response.status = 500
            rval.update({ 'error': str( exc ) })

        return rval

    @web.expose_api
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
        history = self.get_history( trans, history_id, check_ownership=True, check_accessible=False, deleted=True )
        history.deleted = False
        trans.sa_session.add( history )
        trans.sa_session.flush()
        return 'OK'

    @web.expose_api
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
        try:
            history = self.get_history( trans, id, check_ownership=True, check_accessible=True )
            # validation handled here and some parsing, processing, and conversion
            payload = self._validate_and_parse_update_payload( payload )
            # additional checks here (security, etc.)
            changed = self.set_history_from_dict( trans, history, payload )

        except Exception, exception:
            log.error( 'Update of history (%s) failed: %s', id, str( exception ), exc_info=True )
            # convert to appropo HTTP code
            if( isinstance( exception, ValueError )
            or  isinstance( exception, AttributeError ) ):
                # bad syntax from the validater/parser
                trans.response.status = 400
            else:
                trans.response.status = 500
            return { 'error': str( exception ) }

        return changed

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
            if key in ( 'deleted', 'published' ):
                validated_payload[ key ] = self.validate_boolean( key, val )
            elif key == 'tags':
                validated_payload[ key ] = self.validate_and_sanitize_basestring_list( key, val )
            elif key not in valid_but_uneditable_keys:
                pass
                #log.warn( 'unknown key: %s', str( key ) )
        return validated_payload
