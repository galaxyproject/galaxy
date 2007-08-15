"""
Image classes
"""

import data
import logging
from galaxy.datatypes.metadata import MetadataElement
from galaxy.datatypes import metadata
from galaxy import util

log = logging.getLogger(__name__)

class Sequence( data.Text ):
    """Class describing a sequence"""

    """Add metadata elements"""
    MetadataElement( name="dbkey", desc="Database/Build", param=metadata.SelectParameter, multiple=False, values=util.dbnames )

class Alignment( Sequence ):
    """Class describing an alignmnet"""

    """Add metadata elements"""
    MetadataElement( name="species", desc="Species", default=[], param=metadata.SelectParameter, multiple=True, readonly=True, no_value=[] )

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

try:
    import pkg_resources; pkg_resources.require( "bx-python" )
    import bx.align.maf
except:
    pass
class Maf( Alignment ):
    """Class describing a Maf alignment"""
    
    def init_meta( self, dataset, copy_from=None ):
        Alignment.init_meta( self, dataset, copy_from=copy_from )
    
    def set_meta( self, dataset, first_line_is_header=False ):
        """
        Parses and returns species from MAF files.
        """
        species = []
        try:
            maf_reader = bx.align.maf.Reader( open(dataset.file_name) )
            for i, m in enumerate( maf_reader ):
                l = m.components
                for c in l:
                    spec,chrom = bx.align.maf.src_split( c.src )
                    if not spec or not chrom:
                        spec = chrom = c.src
                    if spec not in species:
                        species.append(spec)
                #only check first million blocks for species
                if i > 1000000:
                    break
        except:
            pass
        dataset.metadata.species = species


class Axt( Alignment ):
    """Class describing an axt alignment"""

class Lav( Alignment ):
    """Class describing a LAV alignment"""

