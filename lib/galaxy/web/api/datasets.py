"""
API operations on the contents of a dataset.
"""
import logging, os, string, shutil, urllib, re, socket
from cgi import escape, FieldStorage
from galaxy import util, datatypes, jobs, web, util
from galaxy.web.base.controller import *
from galaxy.util.sanitize_html import sanitize_html
from galaxy.model.orm import *

log = logging.getLogger( __name__ )

class DatasetsController( BaseAPIController, UsesHistoryDatasetAssociation ):

    @web.expose_api
    def index( self, trans, hda_id, **kwd ):
        """
        GET /api/datasets
        Lists datasets.
        """
        pass
        
    @web.expose_api
    def show( self, trans, id, deleted='False', **kwd ):
        """
        GET /api/datasets/{encoded_dataset_id}
        Displays information about and/or content of a dataset.
        """
        
        # Get HDA.
        try:
            hda = self.get_dataset( trans, id, check_ownership=True, check_accessible=True )
        except Exception, e:
            return str( e )
            
        # Return information about HDA.
        rval = None
        try:
            rval = hda.get_api_value()
        except Exception, e:
            rval = "Error in dataset API at listing contents"
            log.error( rval + ": %s" % str(e) )
            trans.response.status = 500
        return rval
