"""
API operations on a history.
"""
import logging, os, string, shutil, urllib, re, socket
from cgi import escape, FieldStorage
from galaxy import util, datatypes, jobs, web, util
from galaxy.web.base.controller import *
from galaxy.util.sanitize_html import sanitize_html
from galaxy.model.orm import *
import galaxy.datatypes
from galaxy.util.bunch import Bunch

import pkg_resources
pkg_resources.require( "Routes" )
import routes

log = logging.getLogger( __name__ )

class HistoriesController( BaseAPIController, UsesHistoryMixin ):

    @web.expose_api
    def index( self, trans, deleted='False', **kwd ):
        """
        GET /api/histories
        GET /api/histories/deleted
        Displays a collection (list) of histories.
        """
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

    @web.expose_api
    def show( self, trans, id, deleted='False', **kwd ):
        """
        GET /api/histories/{encoded_history_id}
        GET /api/histories/deleted/{encoded_history_id}
        GET /api/histories/most_recently_used
        Displays information about a history.
        """
        history_id = id
        params = util.Params( kwd )
        deleted = util.string_as_bool( deleted )

        states = trans.app.model.Dataset.states

        def get_dataset_state_summaries( datasets ):
            # cycles through the history's datasets, building counts and id lists for each possible ds state
            state_counts = {}
            state_ids = {}

            # init counts, ids for each state
            for key, state in states.items():
                state_counts[state] = 0
                state_ids[state] = []

            # cycle through datasets saving each ds' state
            for dataset in datasets:
                dataset_dict = dataset.get_api_value( view='element' )
                item_state = dataset_dict[ 'state' ]

                if not dataset_dict['deleted']:
                    state_counts[ item_state ] = state_counts[ item_state ] + 1

                state_ids[ item_state ].append( trans.security.encode_id( dataset_dict[ 'id' ] ) )

            return ( state_counts, state_ids )

        # try to load the history, by most_recently_used or the given id
        try:
            if history_id == "most_recently_used":
                if trans.user and len( trans.user.galaxy_sessions ) > 0:
                    # Most recent active history for user sessions, not deleted
                    history = trans.user.galaxy_sessions[0].histories[-1].history
                else:
                    return None
            else:
                history = self.get_history( trans, history_id, check_ownership=False,
                                            check_accessible=True, deleted=deleted )

            history_data = history.get_api_value( view='element', value_mapper={'id':trans.security.encode_id} )
            history_data[ 'nice_size' ] = history.get_disk_size( nice_size=True )

            #TODO: separate, move to annotation api, fill on the client
            history_data[ 'annotation' ] = history.get_item_annotation_str( trans.sa_session, trans.user, history )
            if not history_data[ 'annotation' ]:
                history_data[ 'annotation' ] = ''

            # get the history state using the state summaries of it's datasets (default to ERROR)
            num_sets = len([ hda.id for hda in history.datasets if not hda.deleted ])
            state = states.ERROR

            ( state_counts, state_ids ) = get_dataset_state_summaries( history.datasets )

            if num_sets == 0:
                state = states.NEW

            else:
                if( ( state_counts[ states.RUNNING ] > 0 )
                or    ( state_counts[ states.SETTING_METADATA ] > 0 )
                or    ( state_counts[ states.UPLOAD ] > 0 ) ):
                    state = states.RUNNING

                elif state_counts[ states.QUEUED ] > 0:
                    state = states.QUEUED

                elif( ( state_counts[ states.ERROR ] > 0 )
                or  ( state_counts[ states.FAILED_METADATA ] > 0 ) ):
                    state = states.ERROR

                elif state_counts[ states.OK ] == num_sets:
                    state = states.OK

            history_data[ 'state' ] = state
            history_data[ 'state_details' ] = state_counts
            history_data[ 'state_ids' ] = state_ids
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
        params = util.Params( payload )
        hist_name = None
        if payload.get( 'name', None ):
            hist_name = util.restore_text( payload['name'] )
        new_history = trans.app.model.History( user=trans.user, name=hist_name )

        trans.sa_session.add( new_history )
        trans.sa_session.flush()
        item = new_history.get_api_value(view='element', value_mapper={'id':trans.security.encode_id})
        item['url'] = url_for( 'history', id=item['id'] )
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
