"""
API operations on the contents of a dataset from library.
"""
from galaxy import web
from galaxy.web.base.controller import BaseAPIController, UsesLibraryMixinItems

import logging
log = logging.getLogger( __name__ )

class DatasetsController( BaseAPIController, UsesLibraryMixinItems ):

    @web.expose_api
    def index( self, trans, **kwd ):
        """
        GET /api/libraries/datasets
        """
        trans.response.status = 501
        return 'not implemented'

    @web.expose_api
    def show( self, trans, id, **kwd ):
        """
        GET /api/libraries/datasets/{encoded_dataset_id}
        Displays information about and/or content of a dataset identified by the lda ID.
        """
        # Get dataset.
        try:
            dataset = self.get_library_dataset( trans, id = id )
        except Exception, e:
            return str( e )
        try:
            # Default: return dataset as dict.
            rval = dataset.to_dict()
        except Exception, e:
            rval = "Error in dataset API at listing contents: " + str( e )
            log.error( rval + ": %s" % str(e), exc_info=True )
            trans.response.status = 500
        return rval