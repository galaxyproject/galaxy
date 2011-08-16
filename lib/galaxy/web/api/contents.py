"""
API operations on the contents of a library.
"""
import logging, os, string, shutil, urllib, re, socket
from cgi import escape, FieldStorage
from galaxy import util, datatypes, jobs, web, util
from galaxy.web.base.controller import *
from galaxy.util.sanitize_html import sanitize_html
from galaxy.model.orm import *

log = logging.getLogger( __name__ )

class ContentsController( BaseController ):

    @web.expose_api
    def index( self, trans, library_id, **kwd ):
        """
        GET /api/libraries/{encoded_library_id}/contents
        Displays a collection (list) of library contents (files and folders).
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
        try:
            decoded_library_id = trans.security.decode_id( library_id )
        except TypeError:
            trans.response.status = 400
            return "Malformed library id ( %s ) specified, unable to decode." % str( library_id )
        try:
            library = trans.sa_session.query( trans.app.model.Library ).get( decoded_library_id )
        except:
            library = None
        if not library or not ( trans.user_is_admin() or trans.app.security_agent.can_access_library( current_user_roles, library ) ):
            trans.response.status = 400
            return "Invalid library id ( %s ) specified." % str( library_id )
        encoded_id = trans.security.encode_id( 'folder.%s' % library.root_folder.id )
        rval.append( dict( id = encoded_id,
                           type = 'folder',
                           name = '/',
                           url = url_for( 'library_content', library_id=library_id, id=encoded_id ) ) )
        library.root_folder.api_path = ''
        for content in traverse( library.root_folder ):
            encoded_id = trans.security.encode_id( '%s.%s' % ( content.api_type, content.id ) )
            rval.append( dict( id = encoded_id,
                               type = content.api_type,
                               name = content.api_path,
                               url = url_for( 'library_content', library_id=library_id, id=encoded_id, ) ) )
        return rval

    @web.expose_api
    def show( self, trans, id, library_id, **kwd ):
        """
        GET /api/libraries/{encoded_library_id}/contents/{encoded_content_type_and_id}
        Displays information about a library content (file or folder).
        """
        content_id = id
        try:
            decoded_type_and_id = trans.security.decode_string_id( content_id )
            content_type, decoded_content_id = decoded_type_and_id.split( '.' )
        except:
            trans.response.status = 400
            return "Malformed content id ( %s ) specified, unable to decode." % str( content_id )
        if content_type == 'folder':
            model_class = trans.app.model.LibraryFolder
        elif content_type == 'file':
            model_class = trans.app.model.LibraryDataset
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
        return content.get_api_value( view='element' )

    @web.expose_api
    def create( self, trans, library_id, payload, **kwd ):
        """
        POST /api/libraries/{encoded_library_id}/contents
        Creates a new library content item (file or folder).
        """
        create_type = None
        if 'create_type' not in payload:
            trans.response.status = 400
            return "Missing required 'create_type' parameter.  Please consult the API documentation for help."
        else:
            create_type = payload.pop( 'create_type' )
        if create_type not in ( 'file', 'folder' ):
            trans.response.status = 400
            return "Invalid value for 'create_type' parameter ( %s ) specified.  Please consult the API documentation for help." % create_type
        try:
            content_id = str( payload.pop( 'folder_id' ) )
            decoded_type_and_id = trans.security.decode_string_id( content_id )
            parent_type, decoded_parent_id = decoded_type_and_id.split( '.' )
            assert parent_type in ( 'folder', 'file' )
        except:
            trans.response.status = 400
            return "Malformed parent id ( %s ) specified, unable to decode." % content_id
        # "content" can be either a folder or a file, but the parent of new contents can only be folders.
        if parent_type == 'file':
            trans.response.status = 400
            try:
                # With admins or people who can access the dataset provided as the parent, be descriptive.
                dataset = trans.sa_session.query( trans.app.model.LibraryDataset ).get( decoded_parent_id ).library_dataset_dataset_association.dataset
                assert trans.user_is_admin() or trans.app.security_agent.can_access_dataset( trans.get_current_user_roles(), dataset )
                return "The parent id ( %s ) points to a file, not a folder." % content_id
            except:
                # If you can't access the parent we don't want to reveal its existence.
                return "Invalid parent folder id ( %s ) specified." % content_id
        # The rest of the security happens in the library_common controller.
        folder_id = trans.security.encode_id( decoded_parent_id )
        # Now create the desired content object, either file or folder.
        if create_type == 'file':
            status, output = trans.webapp.controllers['library_common'].upload_library_dataset( trans, 'api', library_id, folder_id, **payload )
        elif create_type == 'folder':
            status, output = trans.webapp.controllers['library_common'].create_folder( trans, 'api', folder_id, library_id, **payload )
        if status != 200:
            trans.response.status = status
            # We don't want to reveal the encoded folder_id since it's invalid
            # in the API context.  Instead, return the content_id originally
            # supplied by the client.
            output = output.replace( folder_id, content_id )
            return output
        else:
            rval = []
            for k, v in output.items():
                if type( v ) == trans.app.model.LibraryDatasetDatasetAssociation:
                    v = v.library_dataset
                encoded_id = trans.security.encode_id( create_type + '.' + str( v.id ) )
                rval.append( dict( id = encoded_id,
                                   name = v.name,
                                   url = url_for( 'library_content', library_id=library_id, id=encoded_id ) ) )
            return rval
