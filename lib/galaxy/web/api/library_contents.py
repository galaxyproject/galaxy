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

class LibraryContentsController( BaseAPIController, UsesLibrary, UsesLibraryItems ):

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
        encoded_id = 'F' + trans.security.encode_id( library.root_folder.id )
        rval.append( dict( id = encoded_id,
                           type = 'folder',
                           name = '/',
                           url = url_for( 'library_content', library_id=library_id, id=encoded_id ) ) )
        library.root_folder.api_path = ''
        for content in traverse( library.root_folder ):
            encoded_id = trans.security.encode_id( content.id )
            if content.api_type == 'folder':
                encoded_id = 'F' + encoded_id
            rval.append( dict( id = encoded_id,
                               type = content.api_type,
                               name = content.api_path,
                               url = url_for( 'library_content', library_id=library_id, id=encoded_id, ) ) )
        return rval

    @web.expose_api
    def show( self, trans, id, library_id, **kwd ):
        """
        GET /api/libraries/{encoded_library_id}/contents/{encoded_content_id}
        Displays information about a library content (file or folder).
        """
        class_name, content_id = self.__decode_library_content_id( trans, id )
        if class_name == 'LibraryFolder':
            content = self.get_library_folder( trans, content_id, check_ownership=False, check_accessible=True )
        else:
            content = self.get_library_dataset( trans, content_id, check_ownership=False, check_accessible=True )
        return self.encode_all_ids( trans, content.get_api_value( view='element' ) )

    @web.expose_api
    def create( self, trans, library_id, payload, **kwd ):
        """
        POST /api/libraries/{encoded_library_id}/contents
        Creates a new library content item (file or folder).
        """
        create_type = None
        if 'create_type' not in payload:
            trans.response.status = 400
            return "Missing required 'create_type' parameter."
        else:
            create_type = payload.pop( 'create_type' )
        if create_type not in ( 'file', 'folder' ):
            trans.response.status = 400
            return "Invalid value for 'create_type' parameter ( %s ) specified." % create_type
        if 'folder_id' not in payload:
            trans.response.status = 400
            return "Missing requred 'folder_id' parameter."
        else:
            folder_id = payload.pop( 'folder_id' )
            class_name, folder_id = self.__decode_library_content_id( trans, folder_id )
        try:
            # security is checked in the downstream controller
            parent = self.get_library_folder( trans, folder_id, check_ownership=False, check_accessible=False )
        except Exception, e:
            return str( e )
        # The rest of the security happens in the library_common controller.
        real_folder_id = trans.security.encode_id( parent.id )
        # Now create the desired content object, either file or folder.
        if create_type == 'file':
            status, output = trans.webapp.controllers['library_common'].upload_library_dataset( trans, 'api', library_id, real_folder_id, **payload )
        elif create_type == 'folder':
            status, output = trans.webapp.controllers['library_common'].create_folder( trans, 'api', real_folder_id, library_id, **payload )
        if status != 200:
            trans.response.status = status
            return output
        else:
            rval = []
            for k, v in output.items():
                if type( v ) == trans.app.model.LibraryDatasetDatasetAssociation:
                    v = v.library_dataset
                encoded_id = trans.security.encode_id( v.id )
                if create_type == 'folder':
                    encoded_id = 'F' + encoded_id
                rval.append( dict( id = encoded_id,
                                   name = v.name,
                                   url = url_for( 'library_content', library_id=library_id, id=encoded_id ) ) )
            return rval

    @web.expose_api
    def update( self, trans, id,  library_id, payload, **kwd ):
        """
        PUT /api/libraries/{encoded_library_id}/contents/{encoded_content_type_and_id}
        Sets relationships among items
        """
        if 'converted_dataset_id' in payload:
            converted_id = payload.pop( 'converted_dataset_id' )
            content = self.get_library_dataset( trans, id, check_ownership=False, check_accessible=False )
            content_conv = self.get_library_dataset( trans, converted_id, check_ownership=False, check_accessible=False )
            assoc = trans.app.model.ImplicitlyConvertedDatasetAssociation( parent = content.library_dataset_dataset_association,
                dataset = content_conv.library_dataset_dataset_association,
                file_type = content_conv.library_dataset_dataset_association.extension,
                metadata_safe = True )
            trans.sa_session.add( assoc )
            trans.sa_session.flush()

    def __decode_library_content_id( self, trans, content_id ):
        if ( len( content_id ) % 16 == 0 ):
            return 'LibraryDataset', content_id
        elif ( content_id.startswith( 'F' ) ):
            return 'LibraryFolder', content_id[1:]
        else:
            raise HTTPBadRequest( 'Malformed library content id ( %s ) specified, unable to decode.' % str( content_id ) )
