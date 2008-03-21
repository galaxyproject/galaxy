#!/usr/bin/env python2.4
"""
Provides wrappers and utilities for working with MAF files and alignments.
"""
#Dan Blankenberg
import pkg_resources; pkg_resources.require( "bx-python" )
import bx.align.maf
import bx.intervals
import bx.interval_index_file
import sys, os, string, tempfile

MAF_LOCATION_FILE = "%s/maf_index.loc" % os.environ.get( 'GALAXY_DATA_INDEX_DIR' )

#an object corresponding to a reference layered alignment
class RegionAlignment( object ):
    
    DNA_COMPLEMENT = string.maketrans( "ACGTacgt", "TGCAtgca" )
    MAX_SEQUENCE_SIZE = sys.maxint #Maximum length of sequence allowed
    
    def __init__( self, size, species = [] ):
        assert size <= self.MAX_SEQUENCE_SIZE, "Maximum length allowed for an individual sequence has been exceeded (%i > %i)." % ( size, self.MAX_SEQUENCE_SIZE )
        self.size = size
        self.sequences = {}
        if not isinstance( species, list ):
            species = [species]
        for spec in species:
            self.add_species( spec )
    
    #add a species to the alignment
    def add_species( self, species ):
        #make temporary sequence files
        self.sequences[species] = tempfile.TemporaryFile()
        self.sequences[species].write( "-" * self.size )
    
    #returns the names for species found in alignment, skipping names as requested
    def get_species_names( self, skip = [] ):
        if not isinstance( skip, list ): skip = [skip]
        names = self.sequences.keys()
        for name in skip:
            try: names.remove( name )
            except: pass
        return names
    
    #returns the sequence for a species
    def get_sequence( self, species ):
        self.sequences[species].seek( 0 )
        return self.sequences[species].read()
    
    #returns the reverse complement of the sequence for a species
    def get_sequence_reverse_complement( self, species ):
        complement = [base for base in self.get_sequence( species ).translate( self.DNA_COMPLEMENT )]
        complement.reverse()
        return "".join( complement )
    
    #sets a position for a species
    def set_position( self, index, species, base ):
        if index >= self.size or index < 0: raise "Your index (%i) is out of range (0 - %i)." % ( index, self.size - 1 )
        if len(base) != 1: raise "A genomic position can only have a length of 1."
        if species not in self.sequences.keys(): self.add_species( species )
        self.sequences[species].seek( index )
        self.sequences[species].write( base )
        
    #Flush temp file of specified species, or all species
    def flush( self, species = None ):
        if species is None:
            species = self.sequences.keys()
        elif not isinstance( species, list ):
            species = [species]
        for spec in species:
            self.sequences[spec].flush()

class GenomicRegionAlignment( RegionAlignment ):
    
    def __init__( self, start, end, species = [] ):
        RegionAlignment.__init__( self, end - start, species )
        self.start = start
        self.end = end

class SplicedAlignment( object ):
    
    DNA_COMPLEMENT = string.maketrans( "ACGTacgt", "TGCAtgca" )
    
    def __init__( self, exon_starts, exon_ends, species = [] ):
        if not isinstance( exon_starts, list ):
            exon_starts = [exon_starts]
        if not isinstance( exon_ends, list ):
            exon_ends = [exon_ends]
        assert len( exon_starts ) == len( exon_ends ), "The number of starts does not match the number of sizes."
        self.exons = []
        for i in range( len( exon_starts ) ):
            self.exons.append( GenomicRegionAlignment( exon_starts[i], exon_ends[i], species ) )
    
    #returns the names for species found in alignment, skipping names as requested
    def get_species_names( self, skip = [] ):
        if not isinstance( skip, list ): skip = [skip]
        names = []
        for exon in self.exons:
            for name in exon.get_species_names( skip = skip ):
                if name not in names:
                    names.append( name )
        return names
    
    #returns the sequence for a species
    def get_sequence( self, species ):
        sequence = tempfile.TemporaryFile()
        for exon in self.exons:
            if species in exon.get_species_names():
                sequence.write( exon.get_sequence( species ) )
            else:
                sequence.write( "-" * exon.size )
        sequence.seek( 0 )
        return sequence.read()
    
    #returns the reverse complement of the sequence for a species
    def get_sequence_reverse_complement( self, species ):
        complement = [base for base in self.get_sequence( species ).translate( self.DNA_COMPLEMENT )]
        complement.reverse()
        return "".join( complement )
    
    #Start and end of coding region
    @property
    def start( self ):
        return self.exons[0].start
    @property
    def end( self ):
        return self.exons[-1].end

#Open a MAF index using a UID
def maf_index_by_uid( maf_uid, index_location_file = None ):
    for line in open( index_location_file or MAF_LOCATION_FILE ):
        try:
            #read each line, if not enough fields, go to next line
            if line[0:1] == "#" : continue
            fields = line.split('\t')
            if maf_uid == fields[1]:
                try:
                    maf_files = fields[3].replace( "\n", "" ).replace( "\r", "" ).split( "," )
                    return bx.align.maf.MultiIndexed( maf_files, keep_open = True, parse_e_rows = False )
                except Exception, e:
                    raise 'MAF UID (%s) found, but configuration appears to be malformed: %s' % ( maf_uid, e )
        except:
            pass
    return None

#builds and returns (index, index_filename) for specified maf_file
def build_maf_index( maf_file, species = None ):
    indexes = bx.interval_index_file.Indexes()
    try:
        maf_reader = bx.align.maf.Reader( open( maf_file ) )
        # Need to be a bit tricky in our iteration here to get the 'tells' right
        while True:
            pos = maf_reader.file.tell()
            block = maf_reader.next()
            if block is None: break
            for c in block.components:
                if species is not None and c.src.split( "." )[0] not in species:
                    continue
                indexes.add( c.src, c.forward_strand_start, c.forward_strand_end, pos )
        fd, index_filename = tempfile.mkstemp()
        out = os.fdopen( fd, 'w' )
        indexes.write( out )
        out.close()
        return ( bx.align.maf.Indexed( maf_file, index_filename = index_filename, keep_open = True, parse_e_rows = False ), index_filename )
    except:
        return ( None, None )

#generator yielding only chopped and valid blocks for a specified region
def get_chopped_blocks_for_region( index, src, region, species = None, mincols = 0, force_strand = None ):
    for block in index.get_as_iterator( src, region.start, region.end ):
        ref = block.get_component_by_src( src )
        #We want our block coordinates to be from positive strand
        if ref.strand == "-":
            block = block.reverse_complement()
            ref = block.get_component_by_src( src )
        
        #save old score here for later use
        old_score =  block.score
        slice_start = max( region.start, ref.start )
        slice_end = min( region.end, ref.end )
        
        #slice block by reference species at determined limits
        block = block.slice_by_component( ref, slice_start, slice_end )
        
        if block.text_size > mincols:
            if ( force_strand is None and region.strand != ref.strand ) or ( force_strand is not None and force_strand != ref.strand ):
                block = block.reverse_complement()
            # restore old score, may not be accurate, but it is better than 0 for everything
            block.score = old_score
            if species is not None:
                block = block.limit_to_species( species )
                block.remove_all_gap_columns()
            yield block

#returns a filled region alignment for specified regions
def get_region_alignment( index, primary_species, chrom, start, end, strand = '+', species = None, mincols = 0 ):
    if species is not None: alignment = RegionAlignment( end - start, species )
    else: alignment = RegionAlignment( end - start, primary_species )
    return fill_region_alignment( alignment, index, primary_species, chrom, start, end, strand, species, mincols )

#fills a region alignment 
def fill_region_alignment( alignment, index, primary_species, chrom, start, end, strand = '+', species = None, mincols = 0 ):
    #first step through blocks, save index and score in array, then order by score (array will start as 0=index0,scoreX)
    #step through ordered list, step through maf blocks, stopping at index, store, then break inner loop
    region = bx.intervals.Interval( start, end )
    region.chrom = chrom
    region.strand = strand
    primary_src = "%s.%s" % ( primary_species, chrom )
        
    #Order blocks overlaping this position by score, lowest first
    blocks_order = []
    for i, block in enumerate( get_chopped_blocks_for_region( index, primary_src, region, species, mincols ) ):
        for j in range( 0, len( blocks_order ) ):
            if float( block.score ) < float( blocks_order[j]['score'] ):
                blocks_order.insert( j, {'index':i, 'score':block.score} )
                break
        else:
            blocks_order.append( {'index':i, 'score':block.score} )
    
    #Loop through ordered block indexes and layer blocks by score
    for block_dict in blocks_order:
        for block_index, block in enumerate( get_chopped_blocks_for_region( index, primary_src, region, species, mincols ) ):
            if block_index == block_dict['index']:
                ref = block.get_component_by_src( primary_src )
                #skip gap locations due to insertions in secondary species relative to primary species
                start_offset = ref.start - start
                num_gaps = 0
                for i in range( len( ref.text.rstrip().rstrip("-") ) ):
                    if ref.text[i] in ["-"]:
                        num_gaps += 1
                        continue
                    #Set base for all species
                    for spec in [ c.src.split( '.' )[0] for c in block.components ]:
                        try:
                            #NB: If a gap appears in higher scoring secondary species block,
                            #it will overwrite any bases that have been set by lower scoring blocks
                            #this seems more proper than allowing, e.g. a single base from lower scoring alignment to exist outside of its genomic context
                            alignment.set_position( start_offset + i - num_gaps, spec, block.get_component_by_src_start( spec ).text[i] )
                        except:
                            #species/sequence for species does not exist
                            pass
                break
    return alignment

#returns a filled spliced region alignment for specified region with start and end lists
def get_spliced_region_alignment( index, primary_species, chrom, starts, ends, strand = '+', species = None, mincols = 0 ):
    #create spliced alignment object
    if species is not None: alignment = SplicedAlignment( starts, ends, species )
    else: alignment = SplicedAlignment( starts, ends, [primary_species] )
    for exon in alignment.exons:
        fill_region_alignment( exon, index, primary_species, chrom, exon.start, exon.end, strand, species, mincols)
    return alignment

#loop through string array, only return non-commented lines
def line_enumerator( lines, comment_start = '#' ):
    i = 0
    for line in lines:
        if not line.startswith( comment_start ):
            i += 1
            yield ( i, line )

#read a GeneBed file, return list of starts, ends, raw fields
def get_starts_ends_fields_from_gene_bed( line ):
    #Starts and ends for exons
    starts = []
    ends = []
    
    fields = line.split()
    #Requires atleast 12 BED columns
    if len(fields) < 12:
        raise Exception, "Not a proper 12 column BED line (%s)." % line
    chrom     = fields[0]
    tx_start  = int( fields[1] )
    tx_end    = int( fields[2] )
    name      = fields[3]
    strand    = fields[5]
    if strand != '-': strand='+' #Default strand is +
    cds_start = int( fields[6] )
    cds_end   = int( fields[7] )
    
    #Calculate and store starts and ends of coding exons
    region_start, region_end = cds_start, cds_end
    exon_starts = map( int, fields[11].rstrip( ',\n' ).split( ',' ) )
    exon_starts = map( ( lambda x: x + tx_start ), exon_starts )
    exon_ends = map( int, fields[10].rstrip( ',' ).split( ',' ) )
    exon_ends = map( ( lambda x, y: x + y ), exon_starts, exon_ends );
    for start, end in zip( exon_starts, exon_ends ):
        start = max( start, region_start )
        end = min( end, region_end )
        if start < end:
            starts.append( start )
            ends.append( end )
    return ( starts, ends, fields )
    
def get_species_in_maf( maf_filename ):
        try:
            species={}
            
            file_in = open( maf_filename, 'r' )
            maf_reader = maf.Reader( file_in )
            
            for i, m in enumerate( maf_reader ):
                l = m.components
                for c in l:
                    spec, chrom = maf.src_split( c.src )
                    if not spec or not chrom:
                        spec = chrom = c.src
                    species[spec] = spec
            
            file_in.close()
            
            species = species.keys()
            species.sort()
            return species
        except:
            return []



def remove_temp_index_file( index_filename ):
    try: os.unlink( index_filename )
    except: pass
