"""
Datatype classes for tracks/track views within galaxy.
"""
import logging

from galaxy.datatypes.text import Html
from . import binary

log = logging.getLogger(__name__)


# GeneTrack is no longer supported but leaving the datatype since
# files of this type may still exist
class GeneTrack(binary.Binary):
    edam_data = "data_3002"
    edam_format = "format_2919"
    file_ext = "genetrack"

    def __init__(self, **kwargs):
        super(GeneTrack, self).__init__(**kwargs)
        # self.add_display_app( 'genetrack', 'View in', '', 'genetrack_link' )
    # def get_display_links( self, dataset, type, app, base_url, target_frame='galaxy_main', **kwd ): #Force target_frame to be 'galaxy_main'
    #     return binary.Binary.get_display_links( self, dataset, type, app, base_url, target_frame=target_frame, **kwd )
    # def genetrack_link( self, hda, type, app, base_url ):
    #     ret_val = []
    #     if hda.dataset.has_data():
    # Get the disk file name and data id
    #         file_name = hda.dataset.get_file_name()
    #         data_id  = quote_plus( str( hda.id ) )
    #         galaxy_url = quote_plus( "%s%s" % ( base_url, url_for( controller = 'tool_runner', tool_id='predict2genetrack' ) ) )
    # Make it secure
    #         hashkey = quote_plus( hmac_new( app.config.tool_secret, file_name ) )
    #         encoded = quote_plus( binascii.hexlify( file_name ) )
    #         for name, url in util.get_genetrack_sites():
    #             if name.lower() in app.config.genetrack_display_sites:
    # send both  parameters filename and hashkey
    #                 link = "%s?filename=%s&hashkey=%s&input=%s&GALAXY_URL=%s" % ( url, encoded, hashkey, data_id, galaxy_url )
    #                 ret_val.append( ( name, link ) )
    #         return ret_val


class UCSCTrackHub(Html):
    """
    Datatype for UCSC TrackHub
    """

    file_ext = 'trackhub'
    composite_type = 'auto_primary_file'

    def __init__(self, **kwd):
        Html.__init__(self, **kwd)

    def generate_primary_file(self, dataset=None):
        """
        This is called only at upload to write the html file
        cannot rename the datasets here - they come with the default unfortunately
        """
        rval = [
            '<html><head><title>Files for Composite Dataset (%s)</title></head><p/>\
            This composite dataset is composed of the following files:<p/><ul>' % (
                self.file_ext)]
        for composite_name, composite_file in self.get_composite_files(dataset=dataset).items():
            opt_text = ''
            if composite_file.optional:
                opt_text = ' (optional)'
            rval.append('<li><a href="%s">%s</a>%s' % (composite_name, composite_name, opt_text))
        rval.append('</ul></html>')
        return "\n".join(rval)

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = "Track Hub structure: Visualization in UCSC Track Hub"
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return "Track Hub structure: Visualization in UCSC Track Hub"

    def sniff(self, filename):
        return False
