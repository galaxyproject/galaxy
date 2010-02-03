"""
Datatype classes for tracks/track views within galaxy.
"""

import binary, binascii, logging
from galaxy import util
from galaxy.web import url_for
from galaxy.util.hash_util import hmac_new
import urllib

log = logging.getLogger(__name__)

class GeneTrack( binary.Binary ):
    file_ext = "genetrack"
    
    def __init__(self, **kwargs):
        super( GeneTrack, self ).__init__( **kwargs )
        self.add_display_app( 'genetrack', 'View in', '', 'genetrack_link' )
    def get_display_links( self, dataset, type, app, base_url, target_frame='galaxy_main', **kwd ): #Force target_frame to be 'galaxy_main'
        return binary.Binary.get_display_links( self, dataset, type, app, base_url, target_frame=target_frame, **kwd )
    def genetrack_link( self, hda, type, app, base_url ):
        ret_val = []
        if hda.has_data:
            # Get the disk file name and data id
            file_name = hda.dataset.get_file_name()
            data_id  = urllib.quote_plus( str( hda.id ) ) #can we name this 'input' in the passed params instead of 'id' to prevent GT from having to map 'id' to 'input'?
            galaxy_url = urllib.quote_plus( "%s%s" % ( base_url, url_for( controller = 'tool_runner' ) ) )
            tool_id = urllib.quote_plus( 'predict2genetrack' )
            # Make it secure
            hashkey = urllib.quote_plus( hmac_new( app.config.tool_secret, file_name ) )
            encoded = urllib.quote_plus( binascii.hexlify( file_name ) )
            for name, url in util.get_genetrack_sites():
                if name.lower() in app.config.genetrack_display_sites:
                    # send both  parameters filename and hashkey
                    link = "%s?filename=%s&hashkey=%s&id=%s&GALAXY_URL=%s&tool_id=%s" % ( url, encoded, hashkey, data_id, galaxy_url, tool_id )
                    ret_val.append( ( name, link ) )
            return ret_val
