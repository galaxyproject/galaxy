#!/usr/bin/env python2.4

"""
Reads an interval file and an indexed MAF. Produces a FASTA file containing
the aligned sequences, based upon the provided coordinates

Alignment blocks are layered ontop of each other based upon score.

usage: %prog dbkey_of_interval_file comma_separated_list_of_additional_dbkeys_to_extract maf_file|cached_maf_uid input_interval_file output_fasta_file chromCol startCol endCol strandCol user|cached
"""

#Dan Blankenberg
import pkg_resources; pkg_resources.require( "bx-python" )
import bx.align.maf
import bx.intervals.io
import bx.interval_index_file
import sys, os, tempfile, string

MAF_LOCATION_FILE = "/depot/data2/galaxy/maf_index.loc"

#an object corresponding to a reference layered alignment
class RegionAlignment( object ):
    
    DNA_COMPLEMENT = string.maketrans( "ACGTacgt", "TGCAtgca" )
    
    def __init__( self, size, species = [] ):
        self.size = size
        self.sequences = {}
        if not isinstance( species, list ):
            species = [species]
        for spec in species:
            self.add_species( spec )
    
    #add a species to the alignment
    def add_species( self, species ):
        #make temporary sequence files, need to delete when done
        fd, file_path = tempfile.mkstemp()
        self.sequences[species] = { 'file':os.fdopen( fd, 'w+' ), 'path':file_path }
        self.sequences[species]['file'].write( "-" * self.size )
    
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
        self.sequences[species]['file'].seek( 0 )
        return self.sequences[species]['file'].read()
    
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
        self.sequences[species]['file'].seek( index )
        self.sequences[species]['file'].write( base )
        
    #Flush temp file of specified species, or all species
    def flush( self, species = None ):
        if species is None:
            species = self.sequences.keys()
        elif not isinstance( species, list ):
            species = [species]
        for spec in species:
            self.sequences[spec]['file'].flush()
    
    #object cleanup, delete temporary files
    def __del__( self ):
        for species, sequence in self.sequences.items():
            sequence['file'].close()
            os.unlink( sequence['path'] )

def maf_index_by_uid( maf_uid ):
    for line in open( MAF_LOCATION_FILE ):
        try:
            #read each line, if not enough fields, go to next line
            if line[0:1] == "#" : continue
            fields = line.split('\t')
            if maf_uid == fields[1]:
                try:
                    maf_files = fields[3].replace( "\n", "" ).replace( "\r", "" ).split( "," )
                    return bx.align.maf.MultiIndexed( maf_files, keep_open = True, parse_e_rows = True )
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
        return ( bx.align.maf.Indexed( maf_file, index_filename = index_filename, keep_open = True, parse_e_rows = True ), index_filename )
    except:
        return ( None, None )

def __main__():
    #Parse Command Line
    primary_species = sys.argv.pop( 1 )
    secondary_species = sys.argv.pop( 1 ).split( "," )
    include_primary = True
    if secondary_species == ["None"]:
        secondary_species = None
    else:
        try: secondary_species.remove( primary_species )
        except: include_primary = False
    maf_identifier = sys.argv.pop( 1 )
    interval_file = sys.argv.pop( 1 )
    output_file = sys.argv.pop( 1 )
    try:
        chr_col  = int( sys.argv.pop( 1 ).strip() ) - 1
        start_col = int( sys.argv.pop( 1 ).strip() ) - 1
        end_col = int( sys.argv.pop( 1 ).strip() ) - 1
        strand_col = int( sys.argv.pop( 1 ).strip() ) - 1
        maf_source_type = sys.argv.pop( 1 )
    except:
        print >> sys.stderr, "You appear to be missing metadata. You can specify your metadata by clicking on the pencil icon associated with your interval file."
        sys.exit()
    
    #ensure primary_species is set
    if primary_species == "?": 
        print >> sys.stderr, "You must specify a proper build in order to extract alignments. You can specify your genome build by clicking on the pencil icon associated with your interval file."
        sys.exit()
    
    #get index for mafs based on type 
    index = index_filename = None
    #using specified uid for locally cached
    if maf_source_type.lower() in ["cached"]:
        index = maf_index_by_uid( maf_identifier )
        if index is None:
            print >> sys.stderr, "The MAF source specified (%s) appears to be invalid." % ( maf_identifier )
            sys.exit()
    elif maf_source_type.lower() in ["user"]:
        #index maf for use here, need to remove index_file when finished
        index, index_filename = build_maf_index( maf_identifier, species = [primary_species] )
        if index is None:
            print >> sys.stderr, "Your MAF file appears to be malformed."
            sys.exit()
    else:
        print >> sys.stderr, "Invalid MAF source type specified."
        sys.exit()    
    
    #open output file
    output = open( output_file, "w" )
    
    #Step through interval file
    intervals_extracted = 0
    line_count = 0
    for line_count, region in enumerate( bx.intervals.io.NiceReaderWrapper( open(interval_file, 'r' ), chrom_col = chr_col, start_col = start_col, end_col = end_col, strand_col = strand_col, fix_strand = True, return_header = False, return_comments = False ) ):
        #create alignment object
        if secondary_species is not None: alignment = RegionAlignment( region.end - region.start, [primary_species] + secondary_species )
        else: alignment = RegionAlignment( region.end - region.start, primary_species )
        primary_src = "%s.%s" % ( primary_species, region.chrom )
        
        #Get blocks overlaping this position
        blocks = index.get( primary_src, region.start, region.end )
        #Order the blocks by score, lowest first
        blocks_order = []
        for i, block in enumerate( blocks ):
            for j in range( 0, len( blocks_order ) ):
                if float( block.score ) < float( blocks[blocks_order[j]].score ):
                    blocks_order.insert( j, i )
                    break
            else:
                blocks_order.append( i )
        
        #Loop through ordered block indexes and layer them
        for block_index in blocks_order:
            #Get maf block
            maf = blocks[block_index]
            #Limit maf block to desired species
            if secondary_species is not None:
                maf = maf.limit_to_species( [primary_species] + secondary_species )
            #Colapse extraneous gap columns
            maf.remove_all_gap_columns()
            #Positions and strand are in reference to ref
            ref = maf.get_component_by_src( primary_src )
            #We want our block coordinates to be from positive strand, if region is on negative strand, we will reverse compliment it at the end
            if ref.strand == "-":
                maf = maf.reverse_complement()
                ref = maf.get_component_by_src( primary_src )
            
            #slice maf by start and end
            slice_start = max( region.start, ref.start )
            slice_end = min( region.end, ref.end )
            try:
                maf = maf.slice_by_component( ref, slice_start, slice_end )
                ref = maf.get_component_by_src( primary_src )
            except:
                continue
            
            #skip gap locations due to insertions in secondary species relative to primary species
            start_offset = slice_start - region.start
            num_gaps = 0
            for i in range( len( ref.text.rstrip().rstrip( "-" ) ) ):
                if ref.text[i] in ["-"]:
                    num_gaps += 1
                    continue
                #Set base for all species
                for spec in [ c.src.split( '.' )[0] for c in maf.components ]:
                    try:
                        #NB: If a gap appears in higher scoring secondary species block,
                        #it will overwrite any bases that have been set by lower scoring blocks
                        #this seems more proper than allowing, e.g. a single base from lower scoring alignment to exist outside of its genomic context
                        alignment.set_position( start_offset + i - num_gaps, spec, maf.get_component_by_src_start( spec ).text[i] )
                    except:
                        #species/sequence for species does not exist
                        pass
        
        #Write alignment to output file
        #Output primary species first, if requested
        if include_primary:
            output.write( ">%s.%s(%s):%s-%s\n" %( primary_species, region.chrom, region.strand, region.start, region.end ) )
            if region.strand == "-":
                output.write( alignment.get_sequence_reverse_complement( primary_species ) )
            else:
                output.write( alignment.get_sequence( primary_species ) )
            output.write( "\n" )
        #Output all remainging species
        for spec in secondary_species or alignment.get_species_names( skip = primary_species ):
            output.write( ">%s\n" % ( spec ) )
            if region.strand == "-":
                output.write( alignment.get_sequence_reverse_complement( spec ) )
            else:
                output.write( alignment.get_sequence( spec ) )
            output.write( "\n" )
        
        output.write( "\n" )
        intervals_extracted += 1
    
    output.close()
    
    #remove index file if created during run
    if index_filename is not None:
        os.unlink( index_filename )
    
    #Print message about success for user
    if intervals_extracted > 0:
        print "%i regions were extracted successfully." % ( intervals_extracted )
    else:
        print "No regions were extracted."
        if line_count > 0:
            print "Make sure your metadata is properly set by clicking the pencil icon associated with your interval file."


if __name__ == "__main__": __main__()
