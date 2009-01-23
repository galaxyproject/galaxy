#!/usr/bin/env python
"""
Provides wrappers and utilities for working with MAF files and alignments.
"""
#Dan Blankenberg
import pkg_resources; pkg_resources.require( "bx-python" )
import bx.align.maf
import bx.intervals
import bx.interval_index_file
import sys, os, string, tempfile

assert sys.version_info[:2] >= ( 2, 4 )

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
        if len( base ) != 1: raise "A genomic position can only have a length of 1."
        return self.set_range( index, species, base )
    #sets a range for a species
    def set_range( self, index, species, bases ):
        if index >= self.size or index < 0: raise "Your index (%i) is out of range (0 - %i)." % ( index, self.size - 1 )
        if len( bases ) == 0: raise "A set of genomic positions can only have a positive length."
        if species not in self.sequences.keys(): self.add_species( species )
        self.sequences[species].seek( index )
        self.sequences[species].write( bases )
        
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
def maf_index_by_uid( maf_uid, index_location_file ):
    for line in open( index_location_file ):
        try:
            #read each line, if not enough fields, go to next line
            if line[0:1] == "#" : continue
            fields = line.split('\t')
            if maf_uid == fields[1]:
                try:
                    maf_files = fields[4].replace( "\n", "" ).replace( "\r", "" ).split( "," )
                    return bx.align.maf.MultiIndexed( maf_files, keep_open = True, parse_e_rows = False )
                except Exception, e:
                    raise 'MAF UID (%s) found, but configuration appears to be malformed: %s' % ( maf_uid, e )
        except:
            pass
    return None

#return ( index, temp_index_filename ) for user maf, if available, or build one and return it, return None when no tempfile is created
def open_or_build_maf_index( maf_file, index_filename, species = None ):
    try:
        return ( bx.align.maf.Indexed( maf_file, index_filename = index_filename, keep_open = True, parse_e_rows = False ), None )
    except:
        return build_maf_index( maf_file, species = species )
    

#builds and returns ( index, index_filename ) for specified maf_file
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

def chop_block_by_region( block, src, region, species = None, mincols = 0, force_strand = None ):
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
        return block
    return None
#generator yielding only chopped and valid blocks for a specified region
def get_chopped_blocks_for_region( index, src, region, species = None, mincols = 0, force_strand = None ):
    for block, idx, offset in get_chopped_blocks_with_index_offset_for_region( index, src, region, species, mincols, force_strand ):
        yield block
def get_chopped_blocks_with_index_offset_for_region( index, src, region, species = None, mincols = 0, force_strand = None ):
    for block, idx, offset in index.get_as_iterator_with_index_and_offset( src, region.start, region.end ):
        block = chop_block_by_region( block, src, region, species, mincols, force_strand )
        if block is not None:
            yield block, idx, offset

#returns a filled region alignment for specified regions
def get_region_alignment( index, primary_species, chrom, start, end, strand = '+', species = None, mincols = 0 ):
    if species is not None: alignment = RegionAlignment( end - start, species )
    else: alignment = RegionAlignment( end - start, primary_species )
    return fill_region_alignment( alignment, index, primary_species, chrom, start, end, strand, species, mincols )

#reduces a block to only positions exisiting in the src provided
def reduce_block_by_primary_genome( block, species, chromosome, region_start ):
    #returns ( startIndex, {species:texts}
    #where texts' contents are reduced to only positions existing in the primary genome
    src = "%s.%s" % ( species, chromosome )
    ref = block.get_component_by_src( src )
    start_offset = ref.start - region_start
    species_texts = {}
    for c in block.components:
        species_texts[ c.src.split( '.' )[0] ] = list( c.text )
    #remove locations which are gaps in the primary species, starting from the downstream end
    for i in range( len( species_texts[ species ] ) - 1, -1, -1 ):
        if species_texts[ species ][i] == '-':
            for text in species_texts.values():
                text.pop( i )
    for spec, text in species_texts.items():
        species_texts[spec] = ''.join( text )
    return ( start_offset, species_texts )

#fills a region alignment 
def fill_region_alignment( alignment, index, primary_species, chrom, start, end, strand = '+', species = None, mincols = 0 ):
    region = bx.intervals.Interval( start, end )
    region.chrom = chrom
    region.strand = strand
    primary_src = "%s.%s" % ( primary_species, chrom )
    

    
    #Order blocks overlaping this position by score, lowest first
    blocks = []
    for block, idx, offset in index.get_as_iterator_with_index_and_offset( primary_src, start, end ):
        score = float( block.score )
        for i in range( 0, len( blocks ) ):
            if score < blocks[i][0]:
                blocks.insert( i, ( score, idx, offset ) )
                break
        else:
            blocks.append( ( score, idx, offset ) )
    
    #Loop through ordered blocks and layer by increasing score
    for block_dict in blocks:
        block = chop_block_by_region( block_dict[1].get_at_offset( block_dict[2] ), primary_src, region, species, mincols, strand )
        if block is None: continue
        start_offset, species_texts = reduce_block_by_primary_genome( block, primary_species, chrom, start )
        for spec, text in species_texts.items():
            try:
                alignment.set_range( start_offset, spec, text )
            except:
                #species/sequence for species does not exist
                pass
    
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

def get_fasta_header( component, attributes = {}, suffix = None ):
    header = ">%s(%s):%i-%i|" % ( component.src, component.strand, component.get_forward_strand_start(), component.get_forward_strand_end() )
    for key, value in attributes.iteritems():
        header = "%s%s=%s|" % ( header, key, value )
    if suffix:
        header = "%s%s" % ( header, suffix )
    else:
        header = "%s%s" % ( header, bx.align.src_split( component.src )[ 0 ] )
    return header

def get_attributes_from_fasta_header( header ):
    if not header: return {}
    attributes = {}
    header = header.lstrip( '>' )
    header = header.strip()
    fields = header.split( '|' )
    try:
        region = fields[0]
        region = region.split( '(', 1 )
        temp = region[0].split( '.', 1 )
        attributes['species'] = temp[0]
        if len( temp ) == 2:
            attributes['chrom'] = temp[1]
        else:
            attributes['chrom'] = temp[0]
        region = region[1].split( ')', 1 )
        attributes['strand'] = region[0]
        region = region[1].lstrip( ':' ).split( '-' )
        attributes['start'] = int( region[0] )
        attributes['end'] = int( region[1] )
    except:
        #fields 0 is not a region coordinate
        pass
    if len( fields ) > 2:
        for i in xrange( 1, len( fields ) - 1 ):
            prop = fields[i].split( '=', 1 )
            if len( prop ) == 2:
                attributes[ prop[0] ] = prop[1]
    if len( fields ) > 1:
        attributes['__suffix__'] = fields[-1]
    return attributes

def iter_fasta_alignment( filename ):
    class fastaComponent:
        def __init__( self, species, text = "" ):
            self.species = species
            self.text = text
        def extend( self, text ):
            self.text = self.text + text.replace( '\n', '' ).replace( '\r', '' ).strip()
    #yields a list of fastaComponents for a FASTA file
    f = open( filename, 'rb' )
    components = []
    #cur_component = None
    while True:
        line = f.readline()
        if not line:
            if components:
                yield components
            return
        line = line.strip()
        if not line:
            if components:
                yield components
            components = []
        elif line.startswith( '>' ):
            attributes = get_attributes_from_fasta_header( line )
            components.append( fastaComponent( attributes['species'] ) )
        elif components:
            components[-1].extend( line )

