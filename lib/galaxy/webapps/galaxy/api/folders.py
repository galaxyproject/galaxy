"""
API operations on library folders
"""
# import os
# import shutil
# import urllib
# import re
# import socket
# import traceback
# import string
from galaxy import web
from galaxy import exceptions
from galaxy.web import _future_expose_api as expose_api
from galaxy.web.base.controller import BaseAPIController, UsesLibraryMixin, UsesLibraryMixinItems
from sqlalchemy.orm.exc import MultipleResultsFound
from sqlalchemy.orm.exc import NoResultFound

import logging
log = logging.getLogger( __name__ )


class FoldersController( BaseAPIController, UsesLibraryMixin, UsesLibraryMixinItems ):

    @web.expose_api
    def index( self, trans, **kwd ):
        """
        GET /api/folders/
        This would normally display a list of folders. However, that would
        be across multiple libraries, so it's not implemented.
        """
        raise exceptions.NotImplemented( 'Listing all accessible library folders is not implemented.' )

    @web.expose_api
    def show( self, trans, id, **kwd ):
        """
        show( self, trans, id, **kwd )
        *GET /api/folders/{encoded_folder_id}

        Displays information about a folder.

        :param  id:      the folder's encoded id (required)
        :type   id:      an encoded id string (has to be prefixed by 'F')

        :returns:   dictionary including details of the folder
        :rtype:     dict
        """
        folder_id_without_prefix = self.__cut_the_prefix( id )
        content = self.get_library_folder( trans, folder_id_without_prefix, check_ownership=False, check_accessible=True )
        return_dict = self.encode_all_ids( trans, content.to_dict( view='element' ) )
        return_dict[ 'id' ] = 'F' + return_dict[ 'id' ]
        if return_dict[ 'parent_id' ] is not None:
            return_dict[ 'parent_id' ] = 'F' + return_dict[ 'parent_id' ]
        return return_dict

    @expose_api
    def create( self, trans, encoded_parent_folder_id, **kwd ):

        """
        create( self, trans, encoded_parent_folder_id, **kwd )
        *POST /api/folders/{encoded_parent_folder_id}

        Create a new folder object underneath the one specified in the parameters.

        :param  encoded_parent_folder_id:      the parent folder's id (required)
        :type   encoded_parent_folder_id:      an encoded id string (should be prefixed by 'F')

        :param  name:                          the name of the new folder (required)
        :type   name:                          str

        :param  description:                   the description of the new folder
        :type   description:                   str

        :returns:   information about newly created folder, notably including ID
        :rtype:     dictionary

        :raises: RequestParameterMissingException, MalformedId, InternalServerError
        """

        payload = kwd.get( 'payload', None )
        if payload is None:
            raise exceptions.RequestParameterMissingException( "Missing required parameters 'encoded_parent_folder_id' and 'name'." )
        name = payload.get( 'name', None )
        description = payload.get( 'description', '' )
        if encoded_parent_folder_id is None:
            raise exceptions.RequestParameterMissingException( "Missing required parameter 'encoded_parent_folder_id'." )
        elif name is None:
            raise exceptions.RequestParameterMissingException( "Missing required parameter 'name'." )

        # encoded_parent_folder_id should be prefixed by 'F'
        encoded_parent_folder_id = self.__cut_the_prefix( encoded_parent_folder_id )
        try:
            decoded_parent_folder_id = trans.security.decode_id( encoded_parent_folder_id )
        except ValueError:
            raise exceptions.MalformedId( "Malformed folder id ( %s ) specified, unable to decode" % ( str( id ) ) )

        try:
            parent_folder = trans.sa_session.query( trans.app.model.LibraryFolder ).filter( trans.app.model.LibraryFolder.table.c.id == decoded_parent_folder_id ).one()
        except MultipleResultsFound:
            raise exceptions.InconsistentDatabase( 'Multiple folders found with the same id.' )
        except NoResultFound:
            raise exceptions.RequestParameterInvalidException( 'No folder found with the id provided.' )
        except Exception, e:
            raise exceptions.InternalServerError( 'Error loading from the database.' + str( e ) )

        library = parent_folder.parent_library
        if library.deleted:
            raise exceptions.ObjectAttributeInvalidException( 'You cannot create folder within a deleted library. Undelete it first.' )

        # TODO: refactor the functionality for use here instead of calling another controller
        params = dict( [ ( "name", name ), ( "description", description ) ] )
        status, output = trans.webapp.controllers['library_common'].create_folder( trans, 'api', encoded_parent_folder_id, '', **params )

        if 200 == status and len( output.items() ) == 1:
            for k, v in output.items():
                try:
                    folder = trans.sa_session.query( trans.app.model.LibraryFolder ).get( v.id )
                except Exception, e:
                    raise exceptions.InternalServerError( 'Error loading from the database.' + str( e ))
                if folder:
                    update_time = folder.update_time.strftime( "%Y-%m-%d %I:%M %p" )
                    return_dict = self.encode_all_ids( trans, folder.to_dict( view='element' ) )
                    return_dict[ 'update_time' ] = update_time
                    return_dict[ 'parent_id' ] = 'F' + return_dict[ 'parent_id' ]
                    return_dict[ 'id' ] = 'F' + return_dict[ 'id' ]
                    return return_dict
        else:
            raise exceptions.InternalServerError( 'Error while creating a folder.' + str( e ) )

    @web.expose_api
    def update( self, trans, id,  library_id, payload, **kwd ):
        """
        PUT /api/folders/{encoded_folder_id}

        """
        raise exceptions.NotImplemented( 'Updating folder through this endpoint is not implemented yet.' )

    def __cut_the_prefix(self, encoded_id):

        if ( ( len( encoded_id ) % 16 == 1 ) and encoded_id.startswith( 'F' ) ):
            return encoded_id[ 1: ]
        else:
            raise exceptions.MalformedId( 'Malformed folder id ( %s ) specified, unable to decode.' % str( encoded_id ) )
