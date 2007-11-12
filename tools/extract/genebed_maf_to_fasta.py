#!/usr/bin/env python2.4

"""
Reads a gene BED and an indexed MAF. Produces a FASTA file containing
the aligned gene sequences, based upon the provided coordinates

Alignment blocks are layered ontop of each other based upon score.

usage: %prog dbkey_of_BED comma_separated_list_of_additional_dbkeys_to_extract comma_separated_list_of_indexed_maf_files input_gene_bed_file output_fasta_file cached|user
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
    
    def __init__( self, size, species ):
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
    
    #returns the sequence for a species
    def get_sequence( self, species ):
        self.sequences[species]['file'].seek( 0 )
        return( self.sequences[species]['file'].read() )
    
    #returns the reverse complement of the sequence for a species
    def get_sequence_reverse_complement( self, species ):
        complement = [base for base in self.get_sequence( species ).translate( self.DNA_COMPLEMENT )]
        complement.reverse()
        return "".join( complement )
    
    #sets a position for a species
    def set_position( self, index, species, base ):
        if index >= self.size or index < 0: raise "Your index (%i) is out of range (0 - %i)." % ( index, self.size - 1 )
        if len(base) != 1: raise "A genomic position can only have a length of 1."
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
    try: secondary_species.remove( primary_species )
    except: include_primary = False
    maf_identifier = sys.argv.pop( 1 )
    interval_file = sys.argv.pop( 1 )
    output_file = sys.argv.pop( 1 )
    maf_source_type = sys.argv.pop( 1 )
    
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
            print >> sys.stderr, "The MAF source specified (%s) appears to be invalid." % ( maf_uid )
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
    
    #Step through gene bed
    genes_extracted = 0
    line_count = 0
    for line_count, line in enumerate( open( interval_file, "r" ).readlines() ):
        try:
            if line[0:1]=="#":
                continue
            
            #Storage for exons of this gene
            exons = []
            
            #load gene bed fields
            try:
                fields = line.split()
                #Requires atleast 12 BED columns
                if len(fields) < 12:
                    continue
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
                        alignment = RegionAlignment( end - start, [primary_species] + secondary_species )
                        exons.append( {'ref_start':start, 'ref_end':end, 'alignment':alignment} )
            except Exception, e:
                print "Error loading exon positions from input line %i: %s" % ( line_count, e )
                continue
            
            for exon in exons:
                try:
                    primary_src = "%s.%s" % ( primary_species, chrom )
                    start = exon['ref_start']
                    end = exon['ref_end']
                    alignment = exon['alignment']
                    
                    #Get blocks overlaping this position
                    blocks = index.get( primary_src, start, end )
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
                        slice_start = max( start, ref.start )
                        slice_end = min( end, ref.end )
                        try:
                            maf = maf.slice_by_component( ref, slice_start, slice_end )
                            ref = maf.get_component_by_src( primary_src )
                        except:
                            continue
                        
                        #skip gap locations due to insertions in secondary species relative to primary species
                        start_offset = slice_start - start
                        num_gaps = 0
                        for i in range( len( ref.text.rstrip().rstrip("-") ) ):
                            if ref.text[i] in ["-"]:
                                num_gaps += 1
                                continue
                            #Set base for primary species
                            alignment.set_position( start_offset + i - num_gaps, primary_species, ref.text[i] )
                            #Set base for secondary species
                            for spec in secondary_species:
                                try:
                                    #NB: If a gap appears in higher scoring secondary species block,
                                    #it will overwrite any bases that have been set by lower scoring blocks
                                    #this seems more proper than allowing, e.g. a single base from lower scoring alignment to exist outside of its genomic context
                                    alignment.set_position( start_offset + i - num_gaps, spec, maf.get_component_by_src_start( spec ).text[i] )
                                except:
                                    #species/sequence for species does not exist
                                    pass
                except Exception, e:
                    print "Error filling exons with MAFs from input line %i: %s" % ( line_count, e )
                    continue
                    
            
            #exons loaded, now output them stitched together in proper orientation
            step_list = range(len(exons))
            if strand == "-": step_list.reverse()
            
            #Write alignment to output file
            #Output primary species first, if requested
            if include_primary:
                output.write( ">%s.%s\n" %( primary_species, name ) )
                for i in step_list:
                    alignment = exons[i]['alignment']
                    if strand == "-":
                        output.write( alignment.get_sequence_reverse_complement( primary_species ) )
                    else:
                        output.write( alignment.get_sequence( primary_species ) )
                output.write( "\n" )
            
            #Output all remainging species
            for spec in secondary_species:
                output.write( ">%s.%s\n" % ( spec, name ) )
                for i in step_list:
                    alignment = exons[i]['alignment']
                    if strand == "-":
                        output.write( alignment.get_sequence_reverse_complement( spec ) )
                    else:
                        output.write( alignment.get_sequence( spec ) )
                output.write( "\n" )
            
            output.write( "\n" )
            
            genes_extracted += 1
        
        except Exception, e:
            print "Unexpected error from input line %i: %s" % ( line_count, e )
            continue
    
    #close output file
    output.close()
    
    #remove index file if created during run
    if index_filename is not None:
        os.unlink( index_filename )
    
    #Print message about success for user
    if genes_extracted > 0:
        print "%i genes were extracted successfully." % ( genes_extracted )
    else:
        print "No genes were extracted."
        if line_count > 0:
            print "This tool requires your input file to conform to the 12 column BED standard."

if __name__ == "__main__": __main__()
