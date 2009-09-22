"""
Datatype classes for tracks/track views within galaxy.
"""

import data
import logging
import re
import binascii
from cgi import escape
from galaxy.datatypes.metadata import MetadataElement
from galaxy.datatypes import metadata
import galaxy.model
from galaxy import util
from galaxy.web import url_for
from sniff import *
from galaxy.util.hash_util import *

log = logging.getLogger(__name__)

class GeneTrack( data.Binary ):
    file_ext = "genetrack"
    
    MetadataElement( name="hdf", default="data.hdf", desc="HDF DB", readonly=True, visible=True, no_value=0 )
    MetadataElement( name="sqlite", default="features.sqlite", desc="SQLite Features DB", readonly=True, visible=True, no_value=0 )
    MetadataElement( name="label", default="Custom", desc="Track Label", readonly=True, visible=True, no_value="Custom" )
    
    def __init__(self, **kwargs):
        super( GeneTrack, self ).__init__( **kwargs )
        self.add_display_app( 'genetrack', 'View in GeneTrack', '', 'genetrack_link' )
    def genetrack_link( self, hda, type, app, base_url ):
        ret_val = []
        if hda.has_data:
            # Get the disk file name
            file_name = hda.dataset.get_file_name()
            # Make it secure
            a = hmac_new( app.config.tool_secret, file_name )
            b = binascii.hexlify( file_name )
            encoded_file_name = "%s:%s" % ( a, b )
            for site_name, site_url in util.get_genetrack_sites():
                if site_name in app.config.genetrack_display_sites:
                    link = "%s?filename=%s" % ( site_url, encoded_file_name )
                    ret_val.append( ( site_name, link ) )
            return ret_val
