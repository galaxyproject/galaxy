"""
Image classes
"""

import data
import logging

log = logging.getLogger(__name__)

class Sequence( data.Text ):
    """Class describing a sequence"""
    pass


class Fasta( Sequence ):
    """Class representing a FASTA sequence"""

    def set_peek( self, dataset ):
        Sequence.set_peek( self, dataset )
        count = size = 0
        for line in file( dataset.file_name ):
            if line and line[0] == ">":
                count += 1
            else:
                line = line.strip()
                size += len(line)
        if count == 1:
            dataset.blurb = '%d bases' % size
        else:
            dataset.blurb = '%d sequences' % count

class Maf( Sequence ):
    """Class describing a Maf alignment"""
    pass

class Axt( Sequence ):
    """Class describing an axt alignment"""
    pass
    
class Lav( Sequence ):
    """Class describing a LAV alignment"""
    pass
