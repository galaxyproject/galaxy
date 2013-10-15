"""
API operations allowing clients to determine datatype supported by Galaxy.
"""

from galaxy import web
from galaxy.web.base.controller import BaseAPIController
from galaxy.datatypes.registry import Registry

import logging
log = logging.getLogger( __name__ )

class DatatypesController( BaseAPIController ):
    @web.expose_api
    def index( self, trans, **kwd ):
        """
        GET /api/datatypes
        Return an object containing datatypes.
        """
        try:
            return trans.app.datatypes_registry.upload_file_formats
            
        except Exception, exception:
            log.error( 'could not get datatypes: %s', str( exception ), exc_info=True )
            trans.response.status = 500
            return { 'error': str( exception ) }