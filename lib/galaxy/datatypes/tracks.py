"""
Datatype classes for tracks/track views within galaxy.
"""

import binary, binascii, logging
from galaxy import util
from galaxy.web import url_for
from galaxy.util.hash_util import hmac_new
from urllib import quote_plus

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
        if hda.dataset.has_data():
            # Get the disk file name and data id
            file_name = hda.dataset.get_file_name()
            data_id  = quote_plus( str( hda.id ) )
            galaxy_url = quote_plus( "%s%s" % ( base_url, url_for( controller = 'tool_runner', tool_id='predict2genetrack' ) ) )
            # Make it secure
            hashkey = quote_plus( hmac_new( app.config.tool_secret, file_name ) )
            encoded = quote_plus( binascii.hexlify( file_name ) )
            for name, url in util.get_genetrack_sites():
                if name.lower() in app.config.genetrack_display_sites:
                    # send both  parameters filename and hashkey
                    link = "%s?filename=%s&hashkey=%s&input=%s&GALAXY_URL=%s" % ( url, encoded, hashkey, data_id, galaxy_url )
                    ret_val.append( ( name, link ) )
            return ret_val
