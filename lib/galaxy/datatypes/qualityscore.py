"""
Qualityscore class
"""

import data
import logging
from galaxy.datatypes.sniff import *

log = logging.getLogger(__name__)

class QualityScore ( data.Text ):
    """
    until we know more about quality score formats
    """
    file_ext = "qual"
    
    def set_peek( self, dataset ):
        dataset.peek  = data.get_file_peek( dataset.file_name )
        dataset.blurb = "%s lines, Quality score file" %( data.get_line_count( dataset.file_name ) )
    
    def display_peek(self, dataset):
        try:
            return dataset.peek
        except:
            return "Quality score file (%s)" % ( data.nice_size( dataset.get_size() ) )


      