"""
API operations allowing clients to determine datatype supported by Galaxy.
"""

from galaxy import web
from galaxy.web.base.controller import BaseAPIController
from galaxy.util import asbool

import logging
log = logging.getLogger( __name__ )


class DatatypesController( BaseAPIController ):

    @web.expose_api_anonymous
    def index( self, trans, **kwd ):
        """
        GET /api/datatypes
        Return an object containing upload datatypes.
        """
        extension_only = asbool( kwd.get( 'extension_only', True ) )
        upload_only = asbool( kwd.get( 'upload_only', True ) )
        try:
            if extension_only:
                if upload_only:
                    return trans.app.datatypes_registry.upload_file_formats
                else:
                    return [ ext for ext in trans.app.datatypes_registry.datatypes_by_extension ]
            else:
                rval = []
                for elem in trans.app.datatypes_registry.datatype_elems:
                    if not asbool(elem.get('display_in_upload')) and upload_only:
                        continue
                    keys = ['extension', 'description', 'description_url']
                    dictionary = {}
                    for key in keys:
                        dictionary[key] = elem.get(key)
                    rval.append(dictionary)
                return rval
        except Exception, exception:
            log.error( 'could not get datatypes: %s', str( exception ), exc_info=True )
            trans.response.status = 500
            return { 'error': str( exception ) }

    @web.expose_api_anonymous
    def sniffers( self, trans, **kwd ):
        '''
        GET /api/datatypes/sniffers
        Return a list of sniffers.
        '''
        try:
            rval = []
            for sniffer_elem in trans.app.datatypes_registry.sniffer_elems:
                datatype = sniffer_elem.get( 'type' )
                if datatype is not None:
                    rval.append( datatype )
            return rval
        except Exception, exception:
            log.error( 'could not get datatypes: %s', str( exception ), exc_info=True )
            trans.response.status = 500
            return { 'error': str( exception ) }
