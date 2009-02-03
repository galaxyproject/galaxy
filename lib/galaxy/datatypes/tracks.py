"""
Datatype classes for tracks/track views within galaxy.
"""

import data
import logging
import re
from cgi import escape
from galaxy.datatypes.metadata import MetadataElement
from galaxy.datatypes import metadata
import galaxy.model
from galaxy import util
from galaxy.web import url_for
from sniff import *

log = logging.getLogger(__name__)

class GeneTrack( data.Binary ):
    file_ext = "genetrack"
    
    MetadataElement( name="hdf", default="data.hdf", desc="HDF DB", readonly=True, visible=True, no_value=0 )
    MetadataElement( name="sqlite", default="features.sqlite", desc="SQLite Features DB", readonly=True, visible=True, no_value=0 )
    MetadataElement( name="label", default="Custom", desc="Track Label", readonly=True, visible=True, no_value="Custom" )
    
    def __init__(self, **kwargs):
        super(GeneTrack, self).__init__(**kwargs)
        self.add_display_app( 'genetrack', 'View in ', '', 'genetrack_link' )
    
    def genetrack_link( self, dataset, type, app, base_url ):
        return [('GeneTrack', url_for(controller='genetrack', action='index', dataset_id=dataset.id ))]