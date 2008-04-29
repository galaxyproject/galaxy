"""
Qualityscore class
"""

import data
import logging
from galaxy.datatypes.sniff import *
from galaxy import util

log = logging.getLogger(__name__)

class QualityScore ( data.Text ):
    """
    until we know more about quality score formats
    """
    file_ext = "qual"
    
    def set_peek( self, dataset, line_count=None ):
        dataset.peek  = data.get_file_peek( dataset.file_name )
        if line_count is None:
            dataset.blurb = "%s lines, Quality score file" % util.commaify( str( data.get_line_count( dataset.file_name ) ) )
        else:
            dataset.blurb = "%s lines, Quality score file" % util.commaify( str( line_count ) )
    
    def display_peek(self, dataset):
        try:
            return dataset.peek
        except:
            return "Quality score file (%s)" % ( data.nice_size( dataset.get_size() ) )


      