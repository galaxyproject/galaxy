"""
API operations on a history.
"""

from galaxy import web, util
from galaxy.web.base.controller import BaseAPIController, UsesHistoryMixin
from galaxy.web import url_for
from galaxy.model.orm import desc

import logging
log = logging.getLogger( __name__ )

class HistoriesController( BaseAPIController, UsesHistoryMixin ):

    @web.expose_api_anonymous
    def index( self, trans, deleted='False', **kwd ):
        """
        GET /api/histories
        GET /api/histories/deleted
        Displays a collection (list) of histories.
        """
        #TODO: query (by name, date, etc.)
        rval = []
        deleted = util.string_as_bool( deleted )
        try:
            if trans.user:
                query = trans.sa_session.query(trans.app.model.History ).filter_by( user=trans.user, deleted=deleted ).order_by(
                    desc(trans.app.model.History.table.c.update_time)).all()
                for history in query:
                    item = history.get_api_value(value_mapper={'id':trans.security.encode_id})
                    item['url'] = url_for( 'history', id=trans.security.encode_id( history.id ) )
                    rval.append( item )

            elif trans.galaxy_session.current_history:
                #No user, this must be session authentication with an anonymous user.
                history = trans.galaxy_session.current_history
                item = history.get_api_value(value_mapper={'id':trans.security.encode_id})
                item['url'] = url_for( 'history', id=trans.security.encode_id( history.id ) )
                rval.append(item)

        except Exception, e:
            rval = "Error in history API"
            log.error( rval + ": %s" % str(e) )
            trans.response.status = 500
        return rval

    @web.expose_api_anonymous
    def show( self, trans, id, deleted='False', **kwd ):
        """
        GET /api/histories/{encoded_history_id}
        GET /api/histories/deleted/{encoded_history_id}
        GET /api/histories/most_recently_used
        Displays information about a history.
        """
        #TODO: GET /api/histories/{encoded_history_id}?as_archive=True
        #TODO: GET /api/histories/s/{username}/{slug}
        history_id = id
        deleted = util.string_as_bool( deleted )

        # try to load the history, by most_recently_used or the given id
        try:
            if history_id == "most_recently_used":
                if trans.user and len( trans.user.galaxy_sessions ) > 0:
                    # Most recent active history for user sessions, not deleted
                    history = trans.user.galaxy_sessions[0].histories[-1].history
                    history_id = trans.security.encode_id( history.id )
                else:
                    return None
            else:
                history = self.get_history( trans, history_id, check_ownership=False,
                                            check_accessible=True, deleted=deleted )

            history_data = self.get_history_dict( trans, history )
            history_data[ 'contents_url' ] = url_for( 'history_contents', history_id=history_id )

        except Exception, e:
            msg = "Error in history API at showing history detail: %s" % ( str( e ) )
            log.error( msg, exc_info=True )
            trans.response.status = 500
            return msg

        return history_data

    @web.expose_api
    def create( self, trans, payload, **kwd ):
        """
        POST /api/histories
        Creates a new history.
        """
        hist_name = None
        if payload.get( 'name', None ):
            hist_name = util.restore_text( payload['name'] )
        new_history = trans.app.model.History( user=trans.user, name=hist_name )

        trans.sa_session.add( new_history )
        trans.sa_session.flush()
        item = new_history.get_api_value(view='element', value_mapper={'id':trans.security.encode_id})
        item['url'] = url_for( 'history', id=item['id'] )

        #TODO: copy own history
        #TODO: import an importable history
        #TODO: import from archive
        return item

    @web.expose_api
    def delete( self, trans, id, **kwd ):
        """
        DELETE /api/histories/{encoded_history_id}
        Deletes a history
        """
        history_id = id
        # a request body is optional here
        purge = False
        if kwd.get( 'payload', None ):
            purge = util.string_as_bool( kwd['payload'].get( 'purge', False ) )

        try:
            history = self.get_history( trans, history_id, check_ownership=True, check_accessible=False, deleted=True )
        except Exception, e:
            return str( e )

        history.deleted = True
        if purge and trans.app.config.allow_user_dataset_purge:
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
                    trans.sa_session.flush()
            # Now mark the history as purged
            history.purged = True
            self.sa_session.add( history )

        trans.sa_session.flush()
        return 'OK'

    @web.expose_api
    def undelete( self, trans, id, **kwd ):
        """
        POST /api/histories/deleted/{encoded_history_id}/undelete
        Undeletes a history
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
        PUT /api/histories/{encoded_history_id}
        Changes an existing history.
        """
        #TODO: PUT /api/histories/{encoded_history_id} payload = { rating: rating } (w/ no security checks)
        try:
            history = self.get_history( trans, id, check_ownership=True, check_accessible=True, deleted=True )
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
            # TODO: lots of boilerplate here, but overhead on abstraction is equally onerous
            if   key == 'name':
                if not ( isinstance( val, str ) or isinstance( val, unicode ) ):
                    raise ValueError( 'name must be a string or unicode: %s' %( str( type( val ) ) ) )
                validated_payload[ 'name' ] = util.sanitize_html.sanitize_html( val, 'utf-8' )
                #TODO:?? if sanitized != val: log.warn( 'script kiddie' )
            elif key == 'deleted':
                if not isinstance( val, bool ):
                    raise ValueError( 'deleted must be a boolean: %s' %( str( type( val ) ) ) )
                validated_payload[ 'deleted' ] = val
            elif key == 'published':
                if not isinstance( val, bool ):
                    raise ValueError( 'published must be a boolean: %s' %( str( type( val ) ) ) )
                validated_payload[ 'published' ] = val
            elif key == 'genome_build':
                if not ( isinstance( val, str ) or isinstance( val, unicode ) ):
                    raise ValueError( 'genome_build must be a string: %s' %( str( type( val ) ) ) )
                validated_payload[ 'genome_build' ] = util.sanitize_html.sanitize_html( val, 'utf-8' )
            elif key == 'annotation':
                if not ( isinstance( val, str ) or isinstance( val, unicode ) ):
                    raise ValueError( 'annotation must be a string or unicode: %s' %( str( type( val ) ) ) )
                validated_payload[ 'annotation' ] = util.sanitize_html.sanitize_html( val, 'utf-8' )
            elif key not in valid_but_uneditable_keys:
                raise AttributeError( 'unknown key: %s' %( str( key ) ) )
        return validated_payload

