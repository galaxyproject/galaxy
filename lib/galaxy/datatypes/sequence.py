"""
Image classes
"""

import data
import logging
from galaxy.datatypes.metadata import MetadataElement
from galaxy.datatypes import metadata
from galaxy import util
from sniff import *

log = logging.getLogger(__name__)

class Sequence( data.Text ):
    """Class describing a sequence"""
    def set_readonly_meta( self, dataset ):
        """Resets the values of readonly metadata elements."""
        pass

class Alignment( Sequence ):
    """Class describing an alignmnet"""

    """Add metadata elements"""
    MetadataElement( name="species", desc="Species", default=[], param=metadata.SelectParameter, multiple=True, readonly=True, no_value=None )

class Fasta( Sequence ):
    """Class representing a FASTA sequence"""
    file_ext = "fasta"

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

    def sniff(self, filename):
        """
        Determines whether the file is in fasta format
        
        A sequence in FASTA format consists of a single-line description, followed by lines of sequence data. 
        The first character of the description line is a greater-than (">") symbol in the first column. 
        All lines should be shorter than 80 charcters
        
        For complete details see http://www.g2l.bio.uni-goettingen.de/blast/fastades.html
        
        >>> fname = get_test_fname( 'sequence.maf' )
        >>> Fasta().sniff( fname )
        False
        >>> fname = get_test_fname( 'sequence.fasta' )
        >>> Fasta().sniff( fname )
        True
        """
        headers = get_headers( filename, None )
        data_found = False
        try:
            if len(headers) > 1 and headers[0][0] and headers[0][0][0] == ">":
                for i, l in enumerate( headers ):
                    line = l[0]
                    if i < 1:
                        continue
                    if line:
                        data_found = True
                        try:
                            int( line[0] )
                            return False
                        except:
                            try:
                                elems = line.split()
                                int( elems[0] )
                                return False
                            except:
                                return True
            else:
                return False
            if data_found:
                return True
            else:
                return False
        except:
            return False

try:
    import pkg_resources; pkg_resources.require( "bx-python" )
    import bx.align.maf
except:
    pass

class Maf( Alignment ):
    """Class describing a Maf alignment"""
    file_ext = "maf"

    def init_meta( self, dataset, copy_from=None ):
        Alignment.init_meta( self, dataset, copy_from=copy_from )
    
    def set_meta( self, dataset, first_line_is_header=False, **kwd ):
        """
        Parses and returns species from MAF files.
        """
        species = []
        try:
            for i, m in enumerate( bx.align.maf.Reader( open(dataset.file_name) ) ):
                for c in m.components:
                    ## spec,chrom = bx.align.maf.src_split( c.src )
                    ## if not spec or not chrom: spec = chrom = c.src
                    # "src_split" finds the rightmost dot, which is probably
                    # wrong in general, and certainly here. 
                    spec = c.src
                    if "." in spec:
                        spec = spec.split( "." )[0]
                    if spec not in species: 
                        species.append(spec)
                # only check first 100,000 blocks for species
                if i > 100000: break
        except: 
            pass
        dataset.metadata.species = species
    
    def missing_meta( self, dataset ):
        """Checks to see if species is set"""
        if dataset.metadata.species in [None, []]:
            return True
        return False

    def sniff( self, filename ):
        """
        Determines wether the file is in maf format
        
        The .maf format is line-oriented. Each multiple alignment ends with a blank line. 
        Each sequence in an alignment is on a single line, which can get quite long, but 
        there is no length limit. Words in a line are delimited by any white space. 
        Lines starting with # are considered to be comments. Lines starting with ## can 
        be ignored by most programs, but contain meta-data of one form or another.
        
        The first line of a .maf file begins with ##maf. This word is followed by white-space-separated 
        variable=value pairs. There should be no white space surrounding the "=".
     
        For complete details see http://genome.ucsc.edu/FAQ/FAQformat#format5
        
        >>> fname = get_test_fname( 'sequence.maf' )
        >>> Maf().sniff( fname )
        True
        >>> fname = get_test_fname( 'sequence.fasta' )
        >>> Maf().sniff( fname )
        False
        """
        headers = get_headers( filename, None )
        try:
            if len(headers) > 1 and headers[0][0] and headers[0][0] == "##maf":
                return True
            else:
                return False
        except:
            return False

class Axt( Sequence ):
    """Class describing an axt alignment"""
    file_ext = "axt"

    def sniff( self, filename ):
        """
        Determines whether the file is in axt format
        
        axt alignment files are produced from Blastz, an alignment tool available from Webb Miller's lab 
        at Penn State University.  Each alignment block in an axt file contains three lines: a summary 
        line and 2 sequence lines. Blocks are separated from one another by blank lines.
        
        The summary line contains chromosomal position and size information about the alignment. It consists of 9 required fields:
    
        For complete details see http://genome.ucsc.edu/goldenPath/help/axt.html
        
        >>> fname = get_test_fname( 'alignment.axt' )
        >>> Axt().sniff( fname )
        True
        >>> fname = get_test_fname( 'alignment.lav' )
        >>> Axt().sniff( fname )
        False
       """
        headers = get_headers( filename, None )
        if len(headers) < 4:
            return False
        for hdr in headers:
            if len(hdr) > 0 and hdr[0].startswith("##matrix=axt"):
                return True
            if len(hdr) > 0 and not hdr[0].startswith("#"):
                if len(hdr) != 9:
                    return False
                try:
                    map ( int, [hdr[0], hdr[2], hdr[3], hdr[5], hdr[6], hdr[8]] )
                except:
                    return False
                if hdr[7] not in data.valid_strand:
                    return False
                else:
                    return True

class Lav( Sequence ):
    """Class describing a LAV alignment"""
    file_ext = "lav"

    def sniff( self, filename ):
        """
        Determines whether the file is in lav format
        
        LAV is an alignment format developed by Webb Miller's group. It is the primary output format for BLASTZ.
        The first line of a .lav file begins with #:lav.
    
        For complete details see http://www.bioperl.org/wiki/LAV_alignment_format
        
        >>> fname = get_test_fname( 'alignment.lav' )
        >>> Lav().sniff( fname )
        True
        >>> fname = get_test_fname( 'alignment.axt' )
        >>> Lav().sniff( fname )
        False
        """
        headers = get_headers( filename, None )
        try:
            if len(headers) > 1 and headers[0][0] and headers[0][0].startswith('#:lav'):
                return True
            else:
                return False
        except:
            return False


