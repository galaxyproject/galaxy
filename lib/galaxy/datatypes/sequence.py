"""
Image classes
"""

import data
import logging
import re
from cgi import escape
from galaxy.datatypes.metadata import MetadataElement
from galaxy.datatypes import metadata
import galaxy.model
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
        if not dataset.dataset.purged:
            dataset.peek = data.get_file_peek( dataset.file_name )
            dataset.blurb = data.nice_size( dataset.get_size() )
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def sniff( self, filename ):
        """
        Determines whether the file is in fasta format
        
        A sequence in FASTA format consists of a single-line description, followed by lines of sequence data. 
        The first character of the description line is a greater-than (">") symbol in the first column. 
        All lines should be shorter than 80 charcters
        
        For complete details see http://www.ncbi.nlm.nih.gov/blast/fasta.shtml
        
        Rules for sniffing as True:
            We don't care about line length (other than empty lines).
            The first non-empty line must start with '>' and the Very Next line.strip() must have sequence data and not be a header.
                'sequence data' here is loosely defined as non-empty lines which do not start with '>'
                This will cause Color Space FASTA (csfasta) to be detected as True (they are, after all, still FASTA files - they have a header line followed by sequence data)
                    Previously this method did some checking to determine if the sequence data had integers (presumably to differentiate between fasta and csfasta)
                    This should be done through sniff order, where csfasta (currently has a null sniff function) is detected for first (stricter definition) followed sometime after by fasta
            We will only check that the first purported sequence is correctly formatted.
        
        >>> fname = get_test_fname( 'sequence.maf' )
        >>> Fasta().sniff( fname )
        False
        >>> fname = get_test_fname( 'sequence.fasta' )
        >>> Fasta().sniff( fname )
        True
        """
        
        try:
            fh = open( filename )
            while True:
                line = fh.readline()
                if not line:
                    break #EOF
                line = line.strip()
                if line: #first non-empty line
                    if line.startswith( '>' ):
                        #The next line.strip() must not be '', nor startwith '>'
                        line = fh.readline().strip()
                        if line == '' or line.startswith( '>' ):
                            break
                        return True
                    else:
                        break #we found a non-empty line, but its not a fasta header
        except:
            pass
        return False

class csFasta( Sequence ):
    """ Class representing the SOLID Color-Space sequence ( csfasta ) """
    file_ext = "csfasta"
    
    def set_peek( self, dataset ):
        if not dataset.dataset.purged:
            dataset.peek = data.get_file_peek( dataset.file_name )
            dataset.blurb = data.nice_size( dataset.get_size() )
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def sniff( self, filename ):
        """
        Color-space sequence: 
            >2_15_85_F3
            T213021013012303002332212012112221222112212222
        
        TODO:
            add sniff function
        """
        
        return False
        

                
class FastqSolexa( Sequence ):
    """Class representing a FASTQ sequence ( the Solexa variant )"""
    file_ext = "fastqsolexa"

    def set_peek( self, dataset ):
        if not dataset.dataset.purged:
            dataset.peek = data.get_file_peek( dataset.file_name )
            dataset.blurb = data.nice_size( dataset.get_size() )
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def sniff( self, filename ):
        """
        Determines whether the file is in fastqsolexa format (Solexa Variant)
        For details, see http://maq.sourceforge.net/fastq.shtml

        Note: There are two kinds of FASTQ files, known as "Sanger" (sometimes called "Standard") and Solexa
              These differ in the representation of the quality scores

        >>> fname = get_test_fname( '1.fastqsolexa' )
        >>> FastqSolexa().sniff( fname )
        True
        >>> fname = get_test_fname( '2.fastqsolexa' )
        >>> FastqSolexa().sniff( fname )
        True
        """
        headers = get_headers( filename, None )
        bases_regexp = re.compile( "^[NGTAC]*$" )
        try:
            if len( headers ) >= 4 and headers[0][0] and headers[0][0][0] == "@" and headers[2][0] and headers[2][0][0] == "+" and headers[1][0]:
                # Check the sequence line, make sure it contains only G/C/A/T/N
                if not bases_regexp.match( headers[1][0] ):
                    return False
                
                # Check quality score: integer or ascii char.
                try:
                    check = int(headers[3][0])
                    qscore_int = True
                except:
                    qscore_int = False
                
                if qscore_int:
                    if len( headers[3] ) != len( headers[1][0] ):
                        return False
                else:
                    if len( headers[3][0] ) != len( headers[1][0] ):
                        return False                
                return True 
            return False
        except:
            return False

try:
    from galaxy import eggs
    import pkg_resources; pkg_resources.require( "bx-python" )
    import bx.align.maf
except:
    pass

class Maf( Alignment ):
    """Class describing a Maf alignment"""
    file_ext = "maf"
    
    #Readonly and optional, users can't unset it, but if it is not set, we are generally ok; if required use a metadata validator in the tool definition
    MetadataElement( name="species_chromosomes", desc="Species Chromosomes", param=metadata.FileParameter, readonly=True, no_value=None, visible=False, optional=True )
    MetadataElement( name="maf_index", desc="MAF Index File", param=metadata.FileParameter, readonly=True, no_value=None, visible=False, optional=True )

    def init_meta( self, dataset, copy_from=None ):
        Alignment.init_meta( self, dataset, copy_from=copy_from )
    
    def set_meta( self, dataset, overwrite = True, **kwd ):
        """
        Parses and sets species, chromosomes, index from MAF file.
        """
        #these metadata values are not accessable by users, always overwrite
        
        species = []
        species_chromosomes = {}
        indexes = bx.interval_index_file.Indexes()
        try:
            maf_reader = bx.align.maf.Reader( open( dataset.file_name ) )
            while True:
                pos = maf_reader.file.tell()
                block = maf_reader.next()
                if block is None: break
                for c in block.components:
                    spec = c.src
                    chrom = None
                    if "." in spec:
                        spec, chrom = spec.split( ".", 1 )
                    if spec not in species: 
                        species.append(spec)
                        species_chromosomes[spec] = []
                    if chrom and chrom not in species_chromosomes[spec]:
                        species_chromosomes[spec].append( chrom )
                    indexes.add( c.src, c.forward_strand_start, c.forward_strand_end, pos, max=c.src_size )
        except: #bad MAF file
            pass
        dataset.metadata.species = species
        #only overwrite the contents if our newly determined chromosomes don't match stored
        chrom_file = dataset.metadata.species_chromosomes
        compare_chroms = {}
        if chrom_file:
            try:
                for line in open( chrom_file.file_name ):
                    fields = line.split( "\t" )
                    if fields:
                        spec = fields.pop( 0 )
                        if spec:
                            compare_chroms[spec] = fields
            except:
                pass
        #write out species chromosomes again only if values are different
        if not species_chromosomes or compare_chroms != species_chromosomes:
            tmp_file = tempfile.TemporaryFile( 'w+b' )
            for spec, chroms in species_chromosomes.items():
                tmp_file.write( "%s\t%s\n" % ( spec, "\t".join( chroms ) ) )
            
            if not chrom_file:
                chrom_file = galaxy.model.MetadataFile( dataset = dataset, name = "species_chromosomes" )
                chrom_file.flush()
            tmp_file.seek( 0 )
            open( chrom_file.file_name, 'wb' ).write( tmp_file.read() )
            dataset.metadata.species_chromosomes = chrom_file
            tmp_file.close()
        
        index_file = dataset.metadata.maf_index
        if not index_file:
            index_file = galaxy.model.MetadataFile( dataset = dataset, name="maf_index" )
            index_file.flush()
        indexes.write( open( index_file.file_name, 'w' ) )
        dataset.metadata.maf_index = index_file
    
    def display_peek( self, dataset ):
        """Returns formated html of peek"""
        return self.make_html_table( dataset )

    def make_html_table( self, dataset, skipchars=[] ):
        """Create HTML table, used for displaying peek"""
        out = ['<table cellspacing="0" cellpadding="3">']
        try:
            out.append('<tr><th>Species:&nbsp;')
            for species in dataset.metadata.species:
                out.append( '%s&nbsp;' % species )
            out.append( '</th></tr>' )
            if not dataset.peek:
                dataset.set_peek()
            data = dataset.peek
            lines =  data.splitlines()
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                out.append( '<tr><td>%s</td></tr>' % escape( line ) )
            out.append( '</table>' )
            out = "".join( out )
        except Exception, exc:
            out = "Can't create peek %s" % exc
        return out

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
