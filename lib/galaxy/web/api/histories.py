"""
API operations on a history.
"""
import logging, os, string, shutil, urllib, re, socket
from cgi import escape, FieldStorage
from galaxy import util, datatypes, jobs, web, util
from galaxy.web.base.controller import *
from galaxy.util.sanitize_html import sanitize_html
from galaxy.model.orm import *
from galaxy.model import Dataset
import galaxy.datatypes
from galaxy.util.bunch import Bunch

log = logging.getLogger( __name__ )

class HistoriesController( BaseController ):

    @web.expose_api
    def index( self, trans, **kwd ):
        """
        GET /api/histories
        Displays a collection (list) of histories.
        """               
        try:            
            query = trans.sa_session.query( trans.app.model.History ).filter_by( user=trans.user, deleted=False ).order_by(
                desc(trans.app.model.History.table.c.update_time)).all()           
        except Exception, e:
            log.debug("Error in history API: %s" % str(e))
            
        rval = []
        try:
            for history in query:
                item = history.get_api_value(value_mapper={'id':trans.security.encode_id})
                item['url'] = url_for( 'history', id=trans.security.encode_id( history.id ) )
                # item['id'] = trans.security.encode_id( item['id'] )
                rval.append( item )
        except Exception, e:
            log.debug("Error in history API at constructing return list: %s" % str(e))
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
            states = Dataset.states
            for key, state in states.items():
                rval[state] = 0
            #log.debug("History API: Init rval %s" % rval)
            for dataset in datasets:
                item = dataset.get_api_value( view='element' )
                #log.debug("History API: Set rval %s" % item['state'])
                if not item['deleted']:
                    rval[item['state']] = rval[item['state']] + 1
            return rval            
            
        try:
            decoded_history_id = trans.security.decode_id( history_id )
        except TypeError:
            trans.response.status = 400
            return "Malformed history id ( %s ) specified, unable to decode." % str( history_id )
        try:
            history = trans.sa_session.query(trans.app.model.History).get(decoded_history_id)
            if history.user != trans.user and not trans.user_is_admin():
                if trans.sa_session.query(trans.app.model.HistoryUserShareAssociation).filter_by(user=trans.user, history=history).count() == 0:
                    trans.response.status = 400
                    return("History is not owned by or shared with current user")
        except:
            trans.response.status = 400
            return "That history does not exist."
            
        try:
            item = history.get_api_value(view='element', value_mapper={'id':trans.security.encode_id})
            num_sets = len( [hda.id for hda in history.datasets if not hda.deleted] )            
            states = Dataset.states
            state = states.ERROR
            if num_sets == 0:            
                state = states.NEW
            else:
                summary = traverse(history.datasets)
                #log.debug("History API: Status summary %s" % summary)                
                if summary[states.ERROR] > 0 or summary[states.FAILED_METADATA] > 0:
                    state = states.ERROR
                elif summary[states.RUNNING] > 0 or summary[states.SETTING_METADATA] > 0:
                    state = states.RUNNING
                elif summary[states.QUEUED] > 0:
                    state = states.QUEUED
                elif summary[states.OK] == num_sets:
                    state = states.OK                       
            #item['user'] = item['user'].username
            item['contents_url'] = url_for( 'history_contents', history_id=history_id )
            #item['datasets'] = len( item['datasets'] )
            item['state'] = state
            #log.debug("History API: State %s for %d datasets" % (state, num_sets))
        except Exception, e:
            log.debug("Error in history API at showing history detail: %s" % str(e))
        return item

    @web.expose_api
    def create( self, trans, payload, **kwd ):
        """
        POST /api/histories
        Creates a new history.
        """
        params = util.Params( payload )
        hist_name = util.restore_text( params.get( 'name', None ) )        
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
        params = util.Params( kwd )
        
        try:
            decoded_history_id = trans.security.decode_id( history_id )
        except TypeError:
            trans.response.status = 400
            return "Malformed history id ( %s ) specified, unable to decode." % str( history_id )
        try:
            history = trans.sa_session.query(trans.app.model.History).get(decoded_history_id)
            if history.user != trans.user and not trans.user_is_admin():
                if trans.sa_session.query(trans.app.model.HistoryUserShareAssociation).filter_by(user=trans.user, history=history).count() == 0:
                    trans.response.status = 400
                    return("History is not owned by or shared with current user")
        except:
            trans.response.status = 400
            return "That history does not exist."
        history.deleted = True
        # If deleting the current history, make a new current.
        if history == trans.get_history():
            trans.new_history()
        if trans.app.config.allow_user_dataset_purge:
            for hda in history.datasets:
                hda.purged = True
                trans.sa_session.add( hda )
                if hda.dataset.user_can_purge:
                    try:
                        hda.dataset.full_delete()
                        trans.sa_session.add( hda.dataset )
                    except:
                        trans.sa_session.flush()
