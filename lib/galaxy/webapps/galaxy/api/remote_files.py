"""
API operations on remote files.
"""
import os
import time
import hashlib
from galaxy import exceptions
from galaxy.web import _future_expose_api as expose_api
from galaxy.util import jstree, unicodify
from galaxy.web.base.controller import BaseAPIController
from operator import itemgetter

import logging
log = logging.getLogger( __name__ )


class RemoteFilesAPIController( BaseAPIController ):

    @expose_api
    def index( self, trans, **kwd ):
        """
        GET /api/remote_files/

        Displays remote files.

        :param  target:      target to load available datasets from, defaults to ftp
            possible values: ftp, userdir, importdir
        :type   target:      str

        :param  format:      requested format of data, defaults to flat
            possible values: flat, jstree, ajax

        :returns:   list of available files
        :rtype:     list
        """
        target = kwd.get( 'target', None )
        format = kwd.get( 'format', None )

        if target == 'userdir':
            user_login = trans.user.email
            user_base_dir = trans.app.config.user_library_import_dir
            if user_base_dir is None:
                raise exceptions.ConfigDoesNotAllowException( 'The configuration of this Galaxy instance does not allow upload from user directories.' )
            full_import_dir = os.path.join( user_base_dir, user_login )
            if not os.path.exists(full_import_dir):
                raise exceptions.ObjectNotFound('You do not have any files in your user directory. Use FTP to upload there.')
            if full_import_dir is not None:
                if format == 'jstree':
                    disable = kwd.get( 'disable', 'folders')
                    try:
                        userdir_jstree = self.__create_jstree( full_import_dir, disable )
                        response = userdir_jstree.jsonData()
                    except Exception as exception:
                        log.debug( str( exception ) )
                        raise exceptions.InternalServerError( 'Could not create tree representation of the given folder: ' + str( full_import_dir ) )
                    if not response:
                        raise exceptions.ObjectNotFound('You do not have any files in your user directory. Use FTP to upload there.')
                elif format == 'ajax':
                    raise exceptions.NotImplemented( 'Not implemented yet. Sorry.' )
                else:
                    try:
                        response = self.__load_all_filenames( full_import_dir )
                    except Exception as exception:
                        log.error( 'Could not get user import files: %s', str( exception ), exc_info=True )
                        raise exceptions.InternalServerError( 'Could not get the files from your user directory folder.' )
            else:
                raise exceptions.InternalServerError( 'Could not get the files from your user directory folder.' )
        elif target == 'importdir':
            base_dir = trans.app.config.library_import_dir
            if base_dir is None:
                raise exceptions.ConfigDoesNotAllowException( 'The configuration of this Galaxy instance does not allow usage of import directory.' )
            if format == 'jstree':
                    disable = kwd.get( 'disable', 'folders')
                    try:
                        importdir_jstree = self.__create_jstree( base_dir, disable )
                        response = importdir_jstree.jsonData()
                    except Exception as exception:
                        log.debug( str( exception ) )
                        raise exceptions.InternalServerError( 'Could not create tree representation of the given folder: ' + str( base_dir ) )
            elif format == 'ajax':
                raise exceptions.NotImplemented( 'Not implemented yet. Sorry.' )
            else:
                try:
                    response = self.__load_all_filenames( base_dir )
                except Exception as exception:
                    log.error( 'Could not get user import files: %s', str( exception ), exc_info=True )
                    raise exceptions.InternalServerError( 'Could not get the files from your import directory folder.' )
        else:
            user_ftp_base_dir = trans.app.config.ftp_upload_dir
            if user_ftp_base_dir is None:
                raise exceptions.ConfigDoesNotAllowException( 'The configuration of this Galaxy instance does not allow upload from FTP directories.' )
            try:
                user_ftp_dir = trans.user_ftp_dir
                if user_ftp_dir is not None:
                    response = self.__load_all_filenames( user_ftp_dir )
                else:
                    log.warning( 'You do not have an FTP directory named as your login at this Galaxy instance.' )
                    return None
            except Exception as exception:
                log.warning( 'Could not get ftp files: %s', str( exception ), exc_info=True )
                return None
        return response

    def __load_all_filenames( self, directory ):
        """
        Loads recursively all files within the given folder and its
        subfolders and returns a flat list.
        """
        response = []
        if os.path.exists( directory ):
            for ( dirpath, dirnames, filenames ) in os.walk( directory ):
                for filename in filenames:
                    path = os.path.relpath( os.path.join( dirpath, filename ), directory )
                    statinfo = os.lstat( os.path.join( dirpath, filename ) )
                    response.append( dict( path=path,
                                           size=statinfo.st_size,
                                           ctime=time.strftime( "%m/%d/%Y %I:%M:%S %p", time.localtime( statinfo.st_ctime ) ) ) )
        else:
            log.warning( "The directory \"%s\" does not exist." % directory )
            return response
        # sort by path
        response = sorted(response, key=itemgetter("path"))
        return response

    def __create_jstree( self, directory, disable='folders' ):
        """
        Loads recursively all files and folders within the given folder
        and its subfolders and returns jstree representation
        of its structure.
        """
        userdir_jstree = None
        jstree_paths = []
        if os.path.exists( directory ):
            for ( dirpath, dirnames, filenames ) in os.walk( directory ):
                for dirname in dirnames:
                    dir_path = os.path.relpath( os.path.join( dirpath, dirname ), directory )
                    dir_path_hash = hashlib.sha1(unicodify(dir_path).encode('utf-8')).hexdigest()
                    disabled = True if disable == 'folders' else False
                    jstree_paths.append( jstree.Path( dir_path, dir_path_hash, { 'type': 'folder', 'state': { 'disabled': disabled }, 'li_attr': { 'full_path': dir_path } } ) )

                for filename in filenames:
                    file_path = os.path.relpath( os.path.join( dirpath, filename ), directory )
                    file_path_hash = hashlib.sha1(unicodify(file_path).encode('utf-8')).hexdigest()
                    disabled = True if disable == 'files' else False
                    jstree_paths.append( jstree.Path( file_path, file_path_hash, { 'type': 'file', 'state': { 'disabled': disabled }, 'li_attr': { 'full_path': file_path } } ) )
        else:
            raise exceptions.ConfigDoesNotAllowException( 'The given directory does not exist.' )
        userdir_jstree = jstree.JSTree( jstree_paths )
        return userdir_jstree
