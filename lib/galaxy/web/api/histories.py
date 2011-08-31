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
from galaxy.web.api.util import *

log = logging.getLogger( __name__ )

class HistoriesController( BaseController ):

    @web.expose_api
    def index( self, trans, **kwd ):
        """
        GET /api/histories
        Displays a collection (list) of histories.
        """               
        rval = []

        try:            
            query = trans.sa_session.query( trans.app.model.History ).filter_by( user=trans.user, deleted=False ).order_by(
                desc(trans.app.model.History.table.c.update_time)).all()           
        except Exception, e:
            rval = "Error in history API"
            log.error( rval + ": %s" % str(e) )
            trans.response.status = 500
            
        if not rval:
            try:
                for history in query:
                    item = history.get_api_value(value_mapper={'id':trans.security.encode_id})
                    item['url'] = url_for( 'history', id=trans.security.encode_id( history.id ) )
                    rval.append( item )
            except Exception, e:
                rval = "Error in history API at constructing return list"
                log.error( rval + ": %s" % str(e) )
                trans.response.status = 500
        return rval

    @web.expose_api
    def show( self, trans, id, **kwd ):
        """
        GET /api/histories/{encoded_history_id}
        Displays information about a history.
        """
        history_id = id
        params = util.Params( kwd )
        
        def traverse( datasets ):
            rval = {}
            states = trans.app.model.Dataset.states
            for key, state in states.items():
                rval[state] = 0
            for dataset in datasets:
                item = dataset.get_api_value( view='element' )
                if not item['deleted']:
                    rval[item['state']] = rval[item['state']] + 1
            return rval
            
        try:
            history = get_history_for_access( trans, history_id )
        except Exception, e:
            return str( e )
            
        try:
            item = history.get_api_value(view='element', value_mapper={'id':trans.security.encode_id})
            num_sets = len( [hda.id for hda in history.datasets if not hda.deleted] )            
            states = trans.app.model.Dataset.states
            state = states.ERROR
            if num_sets == 0:
                state = states.NEW
            else:
                summary = traverse(history.datasets)
                if summary[states.ERROR] > 0 or summary[states.FAILED_METADATA] > 0:
                    state = states.ERROR
                elif summary[states.RUNNING] > 0 or summary[states.SETTING_METADATA] > 0:
                    state = states.RUNNING
                elif summary[states.QUEUED] > 0:
                    state = states.QUEUED
                elif summary[states.OK] == num_sets:
                    state = states.OK                       
            item['contents_url'] = url_for( 'history_contents', history_id=history_id )
            item['state'] = state
            item['state_details'] = summary
        except Exception, e:
            item = "Error in history API at showing history detail"
            log.error(item + ": %s" % str(e))
            trans.response.status = 500
        return item

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
            history = get_history_for_modification( trans, history_id )
        except Exception, e:
            return str( e )

        history.deleted = True
        if purge and trans.app.config.allow_user_dataset_purge:
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

        trans.sa_session.flush()
        return 'OK'
