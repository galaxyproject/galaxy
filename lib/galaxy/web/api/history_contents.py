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
        rval = []
        current_user_roles = trans.get_current_user_roles()
        def traverse( folder ):
            admin = trans.user_is_admin()
            rval = []
            for subfolder in folder.active_folders:
                if not admin:
                    can_access, folder_ids = trans.app.security_agent.check_folder_contents( trans.user, current_user_roles, subfolder )
                if (admin or can_access) and not subfolder.deleted:
                    subfolder.api_path = folder.api_path + '/' + subfolder.name
                    subfolder.api_type = 'folder'
                    rval.append( subfolder )
                    rval.extend( traverse( subfolder ) )
            for ld in folder.datasets:
                if not admin:
                    can_access = trans.app.security_agent.can_access_dataset( current_user_roles, ld.library_dataset_dataset_association.dataset )
                if (admin or can_access) and not ld.deleted:
                    ld.api_path = folder.api_path + '/' + ld.name
                    ld.api_type = 'file'
                    rval.append( ld )
            return rval
        #log.debug("Entering Content API for history with %s" % str(history_id))
        try:
            decoded_history_id = trans.security.decode_id( history_id )
        except TypeError:
            trans.response.status = 400
            return "Malformed history id ( %s ) specified, unable to decode." % str( history_id )
        try:
            history = trans.sa_session.query( trans.app.model.History ).get( decoded_history_id )
        except:
            history = None
        if not history or not ( trans.user_is_admin() or trans.app.security_agent.can_access_history( current_user_roles, history ) ):
            trans.response.status = 400
            return "Invalid history id ( %s ) specified." % str( history_id )
        #log.debug("History item %s" % str(history))
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
                content = None
            if not content or ( not trans.user_is_admin() and not trans.app.security_agent.can_access_library_item( trans.get_current_user_roles(), content, trans.user ) ):
                trans.response.status = 400
                return "Invalid %s id ( %s ) specified." % ( content_type, str( content_id ) )
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
        POST /api/libraries/{encoded_library_id}/contents
        Creates a new history content item (file or folder).
        """
        trans.response.status = 403
        return "Not implemented."
