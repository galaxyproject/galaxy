"""
Datatype classes for tracks/track views within galaxy.
"""

import tabular, binascii, logging
from galaxy.datatypes.metadata import MetadataElement
from galaxy.datatypes import metadata
import galaxy.model
from galaxy import util
from galaxy.web import url_for
from sniff import *
from galaxy.util.hash_util import *

log = logging.getLogger(__name__)

class GeneTrack( tabular.Tabular ):
    file_ext = "genetrack"
    
    MetadataElement( name="genetrack", default="data.genetrack", desc="HDF index", readonly=True, visible=True, no_value=0 )
    MetadataElement( name="label", default="Custom", desc="Track Label", readonly=True, visible=True, no_value="Custom" )
    
    def __init__(self, **kwargs):
        super( GeneTrack, self ).__init__( **kwargs )
        self.add_display_app( 'genetrack', 'View in', '', 'genetrack_link' )
    def get_display_links( self, dataset, type, app, base_url, target_frame='galaxy_main', **kwd ):
        return data.Binary.get_display_links( self, dataset, type, app, base_url, target_frame=target_frame, **kwd )
    def genetrack_link( self, hda, type, app, base_url ):
        ret_val = []
        if hda.has_data:
            # Get the disk file name and data id
            file_name = hda.dataset.get_file_name()
            data_id  = hda.dataset.id
            # Make it secure
            hashkey = hmac_new( app.config.tool_secret, file_name )
            encoded = binascii.hexlify( file_name )
            for name, url in util.get_genetrack_sites():
                if name.lower() in app.config.genetrack_display_sites:
                    # send both  parameters filename and hashkey
                    link = "%s?filename=%s&hashkey=%s&id=%s&GALAXY_URL=%s" % ( url, encoded, hashkey, data_id, base_url )
                    ret_val.append( ( name, link ) )
            return ret_val
