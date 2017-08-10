#!/usr/bin/env python
"""
Provides wrappers and utilities for working with MAF files and alignments.
"""
# Dan Blankenberg
from __future__ import print_function

import logging
import os
import resource
import string
import sys
import tempfile
from copy import deepcopy
from errno import EMFILE

import bx.align.maf
import bx.interval_index_file
import bx.intervals
from six.moves import xrange

assert sys.version_info[:2] >= ( 2, 4 )

log = logging.getLogger(__name__)


GAP_CHARS = [ '-' ]
SRC_SPLIT_CHAR = '.'


def src_split( src ):
    fields = src.split( SRC_SPLIT_CHAR, 1 )
    spec = fields.pop( 0 )
    if fields:
        chrom = fields.pop( 0 )
    else:
        chrom = spec
    return spec, chrom


def src_merge( spec, chrom, contig=None ):
    if None in [ spec, chrom ]:
        spec = chrom = spec or chrom
    return bx.align.maf.src_merge( spec, chrom, contig )


def get_species_in_block( block ):
    species = []
    for c in block.components:
        spec, chrom = src_split( c.src )
        if spec not in species:
            species.append( spec )
    return species


def tool_fail( msg="Unknown Error" ):
    print("Fatal Error: %s" % msg, file=sys.stderr)
    sys.exit()


class TempFileHandler( object ):
    '''
    Handles creating, opening, closing, and deleting of Temp files, with a
    maximum number of files open at one time.
    '''

    DEFAULT_MAX_OPEN_FILES = max( resource.getrlimit( resource.RLIMIT_NOFILE )[0] / 2, 1 )

    def __init__( self, max_open_files=None, **kwds ):
        if max_open_files is None:
            max_open_files = self.DEFAULT_MAX_OPEN_FILES
        self.max_open_files = max_open_files
        self.files = []
        self.open_file_indexes = []
        self.kwds = kwds

    def get_open_tempfile( self, index=None, **kwds ):
        if index is not None and index in self.open_file_indexes:
            self.open_file_indexes.remove( index )
        else:
            if self.max_open_files:
                while len( self.open_file_indexes ) >= self.max_open_files:
                    self.close( self.open_file_indexes[0] )
            if index is None:
                index = len( self.files )
                temp_kwds = dict( self.kwds )
                temp_kwds.update( kwds )
                # Being able to use delete=True here, would simplify a bit,
                # but we support python2.4 in these tools
                while True:
                    try:
                        tmp_file = tempfile.NamedTemporaryFile( **temp_kwds )
                        filename = tmp_file.name
                        break
                    except OSError as e:
                        if self.open_file_indexes and e.errno == EMFILE:
                            self.max_open_files = len( self.open_file_indexes )
                            self.close( self.open_file_indexes[0] )
                        else:
                            raise e
                tmp_file.close()
                self.files.append( open( filename, 'w+b' ) )
            else:
                while True:
                    try:
                        self.files[ index ] = open( self.files[ index ].name, 'r+b' )
                        break
                    except OSError as e:
                        if self.open_file_indexes and e.errno == EMFILE:
                            self.max_open_files = len( self.open_file_indexes )
                            self.close( self.open_file_indexes[0] )
                        else:
                            raise e
                self.files[ index ].seek( 0, 2 )
        self.open_file_indexes.append( index )
        return index, self.files[ index ]

    def close( self, index, delete=False ):
        if index in self.open_file_indexes:
            self.open_file_indexes.remove( index )
        rval = self.files[ index ].close()
        if delete:
            try:
                os.unlink( self.files[ index ].name )
            except OSError:
                pass
        return rval

    def flush( self, index ):
        if index in self.open_file_indexes:
            self.files[ index ].flush()

    def __del__( self ):
        for i in xrange( len( self.files ) ):
            self.close( i, delete=True )


# an object corresponding to a reference layered alignment
class RegionAlignment( object ):

    DNA_COMPLEMENT = string.maketrans( "ACGTacgt", "TGCAtgca" )
    MAX_SEQUENCE_SIZE = sys.maxsize  # Maximum length of sequence allowed

    def __init__( self, size, species=[], temp_file_handler=None ):
        assert size <= self.MAX_SEQUENCE_SIZE, "Maximum length allowed for an individual sequence has been exceeded (%i > %i)." % ( size, self.MAX_SEQUENCE_SIZE )
        self.size = size
        if not temp_file_handler:
            temp_file_handler = TempFileHandler()
        self.temp_file_handler = temp_file_handler
        self.sequences = {}
        if not isinstance( species, list ):
            species = [species]
        for spec in species:
            self.add_species( spec )

    # add a species to the alignment
    def add_species( self, species ):
        # make temporary sequence files
        file_index, fh = self.temp_file_handler.get_open_tempfile()
        self.sequences[species] = file_index
        fh.write( "-" * self.size )

    # returns the names for species found in alignment, skipping names as requested
    def get_species_names( self, skip=[] ):
        if not isinstance( skip, list ):
            skip = [skip]
        names = list(self.sequences.keys())
        for name in skip:
            try:
                names.remove( name )
            except:
                pass
        return names

    # returns the sequence for a species
    def get_sequence( self, species ):
        file_index, fh = self.temp_file_handler.get_open_tempfile( self.sequences[species] )
        fh.seek( 0 )
        return fh.read()

    # returns the reverse complement of the sequence for a species
    def get_sequence_reverse_complement( self, species ):
        complement = [base for base in self.get_sequence( species ).translate( self.DNA_COMPLEMENT )]
        complement.reverse()
        return "".join( complement )

    # sets a position for a species
    def set_position( self, index, species, base ):
        if len( base ) != 1:
            raise Exception( "A genomic position can only have a length of 1." )
        return self.set_range( index, species, base )
    # sets a range for a species

    def set_range( self, index, species, bases ):
        if index >= self.size or index < 0:
            raise Exception( "Your index (%i) is out of range (0 - %i)." % ( index, self.size - 1 ) )
        if len( bases ) == 0:
            raise Exception( "A set of genomic positions can only have a positive length." )
        if species not in self.sequences.keys():
            self.add_species( species )
        file_index, fh = self.temp_file_handler.get_open_tempfile( self.sequences[species] )
        fh.seek( index )
        fh.write( bases )

    # Flush temp file of specified species, or all species
    def flush( self, species=None ):
        if species is None:
            species = self.sequences.keys()
        elif not isinstance( species, list ):
            species = [species]
        for spec in species:
            self.temp_file_handler.flush( self.sequences[spec] )


class GenomicRegionAlignment( RegionAlignment ):

    def __init__( self, start, end, species=[], temp_file_handler=None ):
        RegionAlignment.__init__( self, end - start, species, temp_file_handler=temp_file_handler )
        self.start = start
        self.end = end


class SplicedAlignment( object ):

    DNA_COMPLEMENT = string.maketrans( "ACGTacgt", "TGCAtgca" )

    def __init__( self, exon_starts, exon_ends, species=[], temp_file_handler=None ):
        if not isinstance( exon_starts, list ):
            exon_starts = [exon_starts]
        if not isinstance( exon_ends, list ):
            exon_ends = [exon_ends]
        assert len( exon_starts ) == len( exon_ends ), "The number of starts does not match the number of sizes."
        self.exons = []
        if not temp_file_handler:
            temp_file_handler = TempFileHandler()
        self.temp_file_handler = temp_file_handler
        for i in range( len( exon_starts ) ):
            self.exons.append( GenomicRegionAlignment( exon_starts[i], exon_ends[i], species, temp_file_handler=temp_file_handler ) )

    # returns the names for species found in alignment, skipping names as requested
    def get_species_names( self, skip=[] ):
        if not isinstance( skip, list ):
            skip = [skip]
        names = []
        for exon in self.exons:
            for name in exon.get_species_names( skip=skip ):
                if name not in names:
                    names.append( name )
        return names

    # returns the sequence for a species
    def get_sequence( self, species ):
        index, fh = self.temp_file_handler.get_open_tempfile()
        for exon in self.exons:
            if species in exon.get_species_names():
                seq = exon.get_sequence( species )
                # we need to refetch fh here, since exon.get_sequence( species ) uses a tempfile
                # and if max==1, it would close fh
                index, fh = self.temp_file_handler.get_open_tempfile( index )
                fh.write( seq )
            else:
                fh.write( "-" * exon.size )
        fh.seek( 0 )
        rval = fh.read()
        self.temp_file_handler.close( index, delete=True )
        return rval

    # returns the reverse complement of the sequence for a species
    def get_sequence_reverse_complement( self, species ):
        complement = [base for base in self.get_sequence( species ).translate( self.DNA_COMPLEMENT )]
        complement.reverse()
        return "".join( complement )

    # Start and end of coding region
    @property
    def start( self ):
        return self.exons[0].start

    @property
    def end( self ):
        return self.exons[-1].end


# Open a MAF index using a UID
def maf_index_by_uid( maf_uid, index_location_file ):
    for line in open( index_location_file ):
        try:
            # read each line, if not enough fields, go to next line
            if line[0:1] == "#":
                continue
            fields = line.split('\t')
            if maf_uid == fields[1]:
                try:
                    maf_files = fields[4].replace( "\n", "" ).replace( "\r", "" ).split( "," )
                    return bx.align.maf.MultiIndexed( maf_files, keep_open=True, parse_e_rows=False )
                except Exception as e:
                    raise Exception( 'MAF UID (%s) found, but configuration appears to be malformed: %s' % ( maf_uid, e ) )
        except:
            pass
    return None


# return ( index, temp_index_filename ) for user maf, if available, or build one and return it, return None when no tempfile is created
def open_or_build_maf_index( maf_file, index_filename, species=None ):
    try:
        return ( bx.align.maf.Indexed( maf_file, index_filename=index_filename, keep_open=True, parse_e_rows=False ), None )
    except:
        return build_maf_index( maf_file, species=species )


def build_maf_index_species_chromosomes( filename, index_species=None ):
    species = []
    species_chromosomes = {}
    indexes = bx.interval_index_file.Indexes()
    blocks = 0
    try:
        maf_reader = bx.align.maf.Reader( open( filename ) )
        while True:
            pos = maf_reader.file.tell()
            block = next(maf_reader)
            if block is None:
                break
            blocks += 1
            for c in block.components:
                spec = c.src
                chrom = None
                if "." in spec:
                    spec, chrom = spec.split( ".", 1 )
                if spec not in species:
                    species.append( spec )
                    species_chromosomes[spec] = []
                if chrom and chrom not in species_chromosomes[spec]:
                    species_chromosomes[spec].append( chrom )
                if index_species is None or spec in index_species:
                    forward_strand_start = c.forward_strand_start
                    forward_strand_end = c.forward_strand_end
                    try:
                        forward_strand_start = int( forward_strand_start )
                        forward_strand_end = int( forward_strand_end )
                    except ValueError:
                        continue  # start and end are not integers, can't add component to index, goto next component
                        # this likely only occurs when parse_e_rows is True?
                        # could a species exist as only e rows? should the
                    if forward_strand_end > forward_strand_start:
                        # require positive length; i.e. certain lines have start = end = 0 and cannot be indexed
                        indexes.add( c.src, forward_strand_start, forward_strand_end, pos, max=c.src_size )
    except Exception as e:
        # most likely a bad MAF
        log.debug( 'Building MAF index on %s failed: %s' % ( filename, e ) )
        return ( None, [], {}, 0 )
    return ( indexes, species, species_chromosomes, blocks )


# builds and returns ( index, index_filename ) for specified maf_file
def build_maf_index( maf_file, species=None ):
    indexes, found_species, species_chromosomes, blocks = build_maf_index_species_chromosomes( maf_file, species )
    if indexes is not None:
        fd, index_filename = tempfile.mkstemp()
        out = os.fdopen( fd, 'w' )
        indexes.write( out )
        out.close()
        return ( bx.align.maf.Indexed( maf_file, index_filename=index_filename, keep_open=True, parse_e_rows=False ), index_filename )
    return ( None, None )


def component_overlaps_region( c, region ):
    if c is None:
        return False
    start, end = c.get_forward_strand_start(), c.get_forward_strand_end()
    if region.start >= end or region.end <= start:
        return False
    return True


def chop_block_by_region( block, src, region, species=None, mincols=0 ):
    # This chopping method was designed to maintain consistency with how start/end padding gaps have been working in Galaxy thus far:
    #   behavior as seen when forcing blocks to be '+' relative to src sequence (ref) and using block.slice_by_component( ref, slice_start, slice_end )
    #   whether-or-not this is the 'correct' behavior is questionable, but this will at least maintain consistency
    # comments welcome
    slice_start = block.text_size  # max for the min()
    slice_end = 0  # min for the max()
    old_score = block.score  # save old score for later use
    # We no longer assume only one occurance of src per block, so we need to check them all
    for c in iter_components_by_src( block, src ):
        if component_overlaps_region( c, region ):
            if c.text is not None:
                rev_strand = False
                if c.strand == "-":
                    # We want our coord_to_col coordinates to be returned from positive stranded component
                    rev_strand = True
                    c = c.reverse_complement()
                start = max( region.start, c.start )
                end = min( region.end, c.end )
                start = c.coord_to_col( start )
                end = c.coord_to_col( end )
                if rev_strand:
                    # need to orient slice coordinates to the original block direction
                    slice_len = end - start
                    end = len( c.text ) - start
                    start = end - slice_len
                slice_start = min( start, slice_start )
                slice_end = max( end, slice_end )

    if slice_start < slice_end:
        block = block.slice( slice_start, slice_end )
        if block.text_size > mincols:
            # restore old score, may not be accurate, but it is better than 0 for everything?
            block.score = old_score
            if species is not None:
                block = block.limit_to_species( species )
                block.remove_all_gap_columns()
            return block
    return None


def orient_block_by_region( block, src, region, force_strand=None ):
    # loop through components matching src,
    # make sure each of these components overlap region
    # cache strand for each of overlaping regions
    # if force_strand / region.strand not in strand cache, reverse complement
    # we could have 2 sequences with same src, overlapping region, on different strands, this would cause no reverse_complementing
    strands = [ c.strand for c in iter_components_by_src( block, src ) if component_overlaps_region( c, region ) ]
    if strands and ( force_strand is None and region.strand not in strands ) or ( force_strand is not None and force_strand not in strands ):
        block = block.reverse_complement()
    return block


def get_oriented_chopped_blocks_for_region( index, src, region, species=None, mincols=0, force_strand=None ):
    for block, idx, offset in get_oriented_chopped_blocks_with_index_offset_for_region( index, src, region, species, mincols, force_strand ):
        yield block


def get_oriented_chopped_blocks_with_index_offset_for_region( index, src, region, species=None, mincols=0, force_strand=None ):
    for block, idx, offset in get_chopped_blocks_with_index_offset_for_region( index, src, region, species, mincols ):
        yield orient_block_by_region( block, src, region, force_strand ), idx, offset


# split a block with multiple occurances of src into one block per src
def iter_blocks_split_by_src( block, src ):
    for src_c in iter_components_by_src( block, src ):
        new_block = bx.align.Alignment( score=block.score, attributes=deepcopy( block.attributes ) )
        new_block.text_size = block.text_size
        for c in block.components:
            if c == src_c or c.src != src:
                new_block.add_component( deepcopy( c ) )  # components have reference to alignment, dont want to loose reference to original alignment block in original components
        yield new_block


# split a block into multiple blocks with all combinations of a species appearing only once per block
def iter_blocks_split_by_species( block, species=None ):
    def __split_components_by_species( components_by_species, new_block ):
        if components_by_species:
            # more species with components to add to this block
            components_by_species = deepcopy( components_by_species )
            spec_comps = components_by_species.pop( 0 )
            for c in spec_comps:
                newer_block = deepcopy( new_block )
                newer_block.add_component( deepcopy( c ) )
                for value in __split_components_by_species( components_by_species, newer_block ):
                    yield value
        else:
            # no more components to add, yield this block
            yield new_block

    # divide components by species
    spec_dict = {}
    if not species:
        species = []
        for c in block.components:
            spec, chrom = src_split( c.src )
            if spec not in spec_dict:
                spec_dict[ spec ] = []
                species.append( spec )
            spec_dict[ spec ].append( c )
    else:
        for spec in species:
            spec_dict[ spec ] = []
            for c in iter_components_by_src_start( block, spec ):
                spec_dict[ spec ].append( c )

    empty_block = bx.align.Alignment( score=block.score, attributes=deepcopy( block.attributes ) )  # should we copy attributes?
    empty_block.text_size = block.text_size
    # call recursive function to split into each combo of spec/blocks
    for value in __split_components_by_species( list(spec_dict.values()), empty_block ):
        sort_block_components_by_block( value, block )  # restore original component order
        yield value


# generator yielding only chopped and valid blocks for a specified region
def get_chopped_blocks_for_region( index, src, region, species=None, mincols=0 ):
    for block, idx, offset in get_chopped_blocks_with_index_offset_for_region( index, src, region, species, mincols ):
        yield block


def get_chopped_blocks_with_index_offset_for_region( index, src, region, species=None, mincols=0 ):
    for block, idx, offset in index.get_as_iterator_with_index_and_offset( src, region.start, region.end ):
        block = chop_block_by_region( block, src, region, species, mincols )
        if block is not None:
            yield block, idx, offset


# returns a filled region alignment for specified regions
def get_region_alignment( index, primary_species, chrom, start, end, strand='+', species=None, mincols=0, overwrite_with_gaps=True, temp_file_handler=None ):
    if species is not None:
        alignment = RegionAlignment( end - start, species, temp_file_handler=temp_file_handler )
    else:
        alignment = RegionAlignment( end - start, primary_species, temp_file_handler=temp_file_handler )
    return fill_region_alignment( alignment, index, primary_species, chrom, start, end, strand, species, mincols, overwrite_with_gaps )


# reduces a block to only positions exisiting in the src provided
def reduce_block_by_primary_genome( block, species, chromosome, region_start ):
    # returns ( startIndex, {species:texts}
    # where texts' contents are reduced to only positions existing in the primary genome
    src = "%s.%s" % ( species, chromosome )
    ref = block.get_component_by_src( src )
    start_offset = ref.start - region_start
    species_texts = {}
    for c in block.components:
        species_texts[ c.src.split( '.' )[0] ] = list( c.text )
    # remove locations which are gaps in the primary species, starting from the downstream end
    for i in range( len( species_texts[ species ] ) - 1, -1, -1 ):
        if species_texts[ species ][i] == '-':
            for text in species_texts.values():
                text.pop( i )
    for spec, text in species_texts.items():
        species_texts[spec] = ''.join( text )
    return ( start_offset, species_texts )


# fills a region alignment
def fill_region_alignment( alignment, index, primary_species, chrom, start, end, strand='+', species=None, mincols=0, overwrite_with_gaps=True ):
    region = bx.intervals.Interval( start, end )
    region.chrom = chrom
    region.strand = strand
    primary_src = "%s.%s" % ( primary_species, chrom )

    # Order blocks overlaping this position by score, lowest first
    blocks = []
    for block, idx, offset in index.get_as_iterator_with_index_and_offset( primary_src, start, end ):
        score = float( block.score )
        for i in range( 0, len( blocks ) ):
            if score < blocks[i][0]:
                blocks.insert( i, ( score, idx, offset ) )
                break
        else:
            blocks.append( ( score, idx, offset ) )

    # gap_chars_tuple = tuple( GAP_CHARS )
    gap_chars_str = ''.join( GAP_CHARS )
    # Loop through ordered blocks and layer by increasing score
    for block_dict in blocks:
        for block in iter_blocks_split_by_species( block_dict[1].get_at_offset( block_dict[2] ) ):  # need to handle each occurance of sequence in block seperately
            if component_overlaps_region( block.get_component_by_src( primary_src ), region ):
                block = chop_block_by_region( block, primary_src, region, species, mincols )  # chop block
                block = orient_block_by_region( block, primary_src, region )  # orient block
                start_offset, species_texts = reduce_block_by_primary_genome( block, primary_species, chrom, start )
                for spec, text in species_texts.items():
                    # we should trim gaps from both sides, since these are not positions in this species genome (sequence)
                    text = text.rstrip( gap_chars_str )
                    gap_offset = 0
                    # while text.startswith( gap_chars_tuple ):
                    while True in [ text.startswith( gap_char ) for gap_char in GAP_CHARS ]:  # python2.4 doesn't accept a tuple for .startswith()
                        gap_offset += 1
                        text = text[1:]
                        if not text:
                            break
                    if text:
                        if overwrite_with_gaps:
                            alignment.set_range( start_offset + gap_offset, spec, text )
                        else:
                            for i, char in enumerate( text ):
                                if char not in GAP_CHARS:
                                    alignment.set_position( start_offset + gap_offset + i, spec, char )
    return alignment


# returns a filled spliced region alignment for specified region with start and end lists
def get_spliced_region_alignment( index, primary_species, chrom, starts, ends, strand='+', species=None, mincols=0, overwrite_with_gaps=True, temp_file_handler=None ):
    # create spliced alignment object
    if species is not None:
        alignment = SplicedAlignment( starts, ends, species, temp_file_handler=temp_file_handler )
    else:
        alignment = SplicedAlignment( starts, ends, [primary_species], temp_file_handler=temp_file_handler )
    for exon in alignment.exons:
        fill_region_alignment( exon, index, primary_species, chrom, exon.start, exon.end, strand, species, mincols, overwrite_with_gaps )
    return alignment


# loop through string array, only return non-commented lines
def line_enumerator( lines, comment_start='#' ):
    i = 0
    for line in lines:
        if not line.startswith( comment_start ):
            i += 1
            yield ( i, line )


# read a GeneBed file, return list of starts, ends, raw fields
def get_starts_ends_fields_from_gene_bed( line ):
    # Starts and ends for exons
    starts = []
    ends = []

    fields = line.split()
    # Requires atleast 12 BED columns
    if len(fields) < 12:
        raise Exception( "Not a proper 12 column BED line (%s)." % line )
    tx_start = int( fields[1] )
    strand = fields[5]
    if strand != '-':
        strand = '+'  # Default strand is +
    cds_start = int( fields[6] )
    cds_end = int( fields[7] )

    # Calculate and store starts and ends of coding exons
    region_start, region_end = cds_start, cds_end
    exon_starts = list(map( int, fields[11].rstrip( ',\n' ).split( ',' ) ))
    exon_starts = [x + tx_start for x in exon_starts]
    exon_ends = list(map( int, fields[10].rstrip( ',' ).split( ',' ) ))
    exon_ends = [x + y for x, y in zip( exon_starts, exon_ends )]
    for start, end in zip( exon_starts, exon_ends ):
        start = max( start, region_start )
        end = min( end, region_end )
        if start < end:
            starts.append( start )
            ends.append( end )
    return ( starts, ends, fields )


def iter_components_by_src( block, src ):
    for c in block.components:
        if c.src == src:
            yield c


def get_components_by_src( block, src ):
    return [ value for value in iter_components_by_src( block, src ) ]


def iter_components_by_src_start( block, src ):
    for c in block.components:
        if c.src.startswith( src ):
            yield c


def get_components_by_src_start( block, src ):
    return [ value for value in iter_components_by_src_start( block, src ) ]


def sort_block_components_by_block( block1, block2 ):
    # orders the components in block1 by the index of the component in block2
    # block1 must be a subset of block2
    # occurs in-place
    return block1.components.sort( cmp=lambda x, y: block2.components.index( x ) - block2.components.index( y ) )


def get_species_in_maf( maf_filename ):
    species = []
    for block in bx.align.maf.Reader( open( maf_filename ) ):
        for spec in get_species_in_block( block ):
            if spec not in species:
                species.append( spec )
    return species


def parse_species_option( species ):
    if species:
        species = species.split( ',' )
        if 'None' not in species:
            return species
    return None  # provided species was '', None, or had 'None' in it


def remove_temp_index_file( index_filename ):
    try:
        os.unlink( index_filename )
    except:
        pass

# Below are methods to deal with FASTA files


def get_fasta_header( component, attributes={}, suffix=None ):
    header = ">%s(%s):%i-%i|" % ( component.src, component.strand, component.get_forward_strand_start(), component.get_forward_strand_end() )
    for key, value in attributes.items():
        header = "%s%s=%s|" % ( header, key, value )
    if suffix:
        header = "%s%s" % ( header, suffix )
    else:
        header = "%s%s" % ( header, src_split( component.src )[ 0 ] )
    return header


def get_attributes_from_fasta_header( header ):
    if not header:
        return {}
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
        # fields 0 is not a region coordinate
        pass
    if len( fields ) > 2:
        for i in range( 1, len( fields ) - 1 ):
            prop = fields[i].split( '=', 1 )
            if len( prop ) == 2:
                attributes[ prop[0] ] = prop[1]
    if len( fields ) > 1:
        attributes['__suffix__'] = fields[-1]
    return attributes


def iter_fasta_alignment( filename ):
    class fastaComponent:
        def __init__( self, species, text="" ):
            self.species = species
            self.text = text

        def extend( self, text ):
            self.text = self.text + text.replace( '\n', '' ).replace( '\r', '' ).strip()
    # yields a list of fastaComponents for a FASTA file
    f = open( filename, 'rb' )
    components = []
    # cur_component = None
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
