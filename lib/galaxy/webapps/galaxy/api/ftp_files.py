"""
API operations on ftp files.
"""
import logging
from galaxy.web.base.controller import BaseAPIController, url_for
from galaxy import web
import os.path
import os
import time
from operator import itemgetter

log = logging.getLogger( __name__ )

class FTPFilesAPIController( BaseAPIController ):
    @web.expose_api
    def index( self, trans, **kwd ):
        """
        GET /api/ftp_files/
        Displays local files.
        """
        
        # look for ftp files
        try:
            # initialize response
            response = []
            
            # identify ftp directory
            user_ftp_base_dir = trans.app.config.ftp_upload_dir
            if user_ftp_base_dir is None:
                return []
        
            # identify user sub directory
            user_ftp_dir = None
            if user_ftp_base_dir is not None and trans is not None and trans.user is not None:
                identifier = trans.app.config.ftp_upload_dir_identifier
                user_ftp_dir = os.path.join( user_ftp_base_dir, getattr(trans.user, identifier) )
            if user_ftp_dir is None:
                return []

            # read directory
            if os.path.exists( user_ftp_dir ):
                for ( dirpath, dirnames, filenames ) in os.walk( user_ftp_dir ):
                    for filename in filenames:
                        path = os.path.relpath( os.path.join( dirpath, filename ), user_ftp_dir )
                        statinfo = os.lstat( os.path.join( dirpath, filename ) )
                        response.append( dict(  path    = path,
                                                size    = statinfo.st_size,
                                                ctime   = time.strftime( "%m/%d/%Y %I:%M:%S %p", time.localtime( statinfo.st_ctime ) ) ) )
            
                # sort by path
                response = sorted(response, key=itemgetter("path"))

            # return
            return response
        
        except Exception, exception:
            log.error( 'could not get ftp files: %s', str( exception ), exc_info=True )
            trans.response.status = 500
            return { 'error': str( exception ) }

