"""
API operations on the contents of a history.
"""
import logging, os, string, shutil, urllib, re, socket
from cgi import escape, FieldStorage
from galaxy import util, datatypes, jobs, web, util
from galaxy.web.base.controller import *
from galaxy.util.sanitize_html import sanitize_html
from galaxy.model.orm import *

import pkg_resources
pkg_resources.require( "Routes" )
import routes

log = logging.getLogger( __name__ )

class HistoryContentsController( BaseController ):

    @web.expose_api
    def index( self, trans, history_id, **kwd ):
        """
        GET /api/histories/{encoded_history_id}/contents
        Displays a collection (list) of history contents
        """        
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
                       
        rval = []
        try:
            for dataset in history.datasets:
                api_type = "file"
                encoded_id = trans.security.encode_id( '%s.%s' % (api_type, dataset.id) )
                #log.debug("History dataset %s" % str(encoded_id))
                rval.append( dict( id = encoded_id,
                                   type = api_type,
                                   name = dataset.name,
                                   url = url_for( 'history_content', history_id=history_id, id=encoded_id, ) ) )
        except Exception, e:
            log.debug("Error in history API at listing contents: %s" % str(e))
        return rval

    @web.expose_api
    def show( self, trans, id, history_id, **kwd ):
        """
        GET /api/histories/{encoded_history_id}/contents/{encoded_content_type_and_id}
        Displays information about a history content dataset.
        """
        #log.debug("Entering Content API for history dataset with %s" % str(history_id))
        try:
            content_id = id
            try:
                decoded_type_and_id = trans.security.decode_string_id( content_id )
                content_type, decoded_content_id = decoded_type_and_id.split( '.' )
            except:
                trans.response.status = 400
                return "Malformed content id ( %s ) specified, unable to decode." % str( content_id )
            if content_type == 'file':
                model_class = trans.app.model.HistoryDatasetAssociation
            else:
                trans.response.status = 400
                return "Invalid type ( %s ) specified." % str( content_type )
            try:
                content = trans.sa_session.query( model_class ).get( decoded_content_id )
            except:
                trans.response.status = 400
                return "Invalid %s id ( %s ) specified." % ( content_type, str( content_id ) )
            if content.history.user != trans.user and not trans.user_is_admin():
                if trans.sa_session.query(trans.app.model.HistoryUserShareAssociation).filter_by(user=trans.user, history=history).count() == 0:
                    trans.response.status = 400
                    return("History is not owned by or shared with current user")                      
            item = content.get_api_value( view='element' )
            if not item['deleted']:
                # Problem: Method url_for cannot use the dataset controller
                # Get the environment from DefaultWebTransaction and use default webapp mapper instead of webapp API mapper
                url = routes.URLGenerator(trans.webapp.mapper, trans.environ)
                # http://routes.groovie.org/generating.html
                # url_for is being phased out, so new applications should use url
                item['download_url'] = url(controller='dataset', action='display', dataset_id=trans.security.encode_id(decoded_content_id), to_ext=content.ext)
        except Exception, e:
            log.debug("Error in history API at listing dataset: %s" % str(e))               
        return item

    @web.expose_api
    def create( self, trans, history_id, payload, **kwd ):
        """
        POST /api/libraries/{encoded_history_id}/contents
        Creates a new history content item.        """          
        params = util.Params( payload )
        history_id = util.restore_text( params.get( 'history_id', None ) )
        ldda_id = util.restore_text( params.get( 'ldda_id', None ) )
        add_to_history = True               
        decoded_history_id = trans.security.decode_id( history_id )
        ld_t, ld_id = trans.security.decode_string_id(ldda_id).split('.')
        history = trans.sa_session.query(trans.app.model.History).get(decoded_history_id)
        ldda = trans.sa_session.query(self.app.model.LibraryDatasetDatasetAssociation).get(ld_id)
        hda = ldda.to_history_dataset_association(history, add_to_history=add_to_history)        
        history.add_dataset(hda)
