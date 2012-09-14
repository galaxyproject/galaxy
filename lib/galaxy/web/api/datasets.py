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

def is_true ( a_str ):
    return is_true == True or a_str in [ 'True', 'true', 'T', 't' ]

class DatasetsController( BaseAPIController, UsesVisualizationMixin ):

    @web.expose_api
    def index( self, trans, **kwd ):
        """
        GET /api/datasets
        Lists datasets.
        """
        pass
        
    @web.expose_api
    def show( self, trans, id, hda_ldda='hda', deleted='False', **kwd ):
        """
        GET /api/datasets/{encoded_dataset_id}
        Displays information about and/or content of a dataset.
        """

        # Process arguments.
        track_config = is_true( kwd.get( 'track_config', False ) )
        
        # Get dataset.
        try:
            dataset = self.get_hda_or_ldda( trans, hda_ldda=hda_ldda, dataset_id=id )
        except Exception, e:
            return str( e )

        # Return info.
        rval = None
        if track_config:
            rval = self.get_new_track_config( trans, dataset )
        else:
            # Default: return dataset as API value.
            try:
                rval = dataset.get_api_value()
            except Exception, e:
                rval = "Error in dataset API at listing contents"
                log.error( rval + ": %s" % str(e) )
                trans.response.status = 500
        return rval
