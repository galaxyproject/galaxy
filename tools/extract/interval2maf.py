#!/usr/bin/env python2.4

"""
Reads a list of intervals and a maf. Produces a new maf containing the
blocks or parts of blocks in the original that overlapped the intervals.

If a MAF file, not UID, is provided the MAF file is indexed before being processed.

NOTE: If two intervals overlap the same block it will be written twice.

usage: %prog maf_file [options]
   -d, --dbkey=d: Database key, ie hg17
   -c, --chromCol=c: Column of Chr
   -s, --startCol=s: Column of Start
   -e, --endCol=e: Column of End
   -S, --strandCol=S: Column of Strand
   -t, --mafType=t: Type of MAF source to use
   -m, --mafFile=m: Path of source MAF file, if not using cached version
   -i, --interval_file=i:       Input interval file
   -o, --output_file=o:      Output MAF file
   -p, --species=p: Species to include in output
"""

#Dan Blankenberg
import pkg_resources; pkg_resources.require( "bx-python" )
from bx.cookbook import doc_optparse
import bx.align.maf
import bx.intervals.io
import bx.interval_index_file
import sys, os

MAF_LOCATION_FILE = "/depot/data2/galaxy/maf_index.loc"

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
    # Parse Command Line
    options, args = doc_optparse.parse( __doc__ )
    
    index = index_filename = None
    mincols = 0
    
    try:
        if options.dbkey: dbkey = options.dbkey
        else: dbkey = None
        if dbkey in [None, "?"]:
            print >>sys.stderr, "You must specify a proper build in order to extract alignments. You can specify your genome build by clicking on the pencil icon associated with your interval file."
            sys.exit()
        
        if options.species: species = options.species.split( ',' )
        else: species = None
        
        if options.chromCol: chromCol= int(options.chromCol) - 1
        else: 
            print >>sys.stderr, "Chromosome column has not been specified."
            sys.exit()
        
        if options.startCol: startCol= int(options.startCol) - 1
        else: 
            print >>sys.stderr, "Start column has not been specified."
            sys.exit()
        
        if options.endCol: endCol= int(options.endCol) - 1
        else: 
            print >>sys.stderr, "End column has not been specified."
            sys.exit()
        
        if options.strandCol: strandCol= int(options.strandCol) - 1
        else: 
            print >>sys.stderr, "Strand column has not been specified."
            sys.exit()
                
        if options.interval_file: interval_file= options.interval_file
        else: 
            print >>sys.stderr, "Input interval file has not been specified."
            sys.exit()
        
        if options.output_file: output_file= options.output_file
        else: 
            print >>sys.stderr, "Output file has not been specified."
            sys.exit()
        
        #Open indexed access to MAFs
        if options.mafType:
            index = maf_index_by_uid( options.mafType )
            if index is None:
                print >> sys.stderr, "The MAF source specified (%s) appears to be invalid." % ( options.mafType )
                sys.exit()
        elif options.mafFile:
            index, index_filename = build_maf_index( options.mafFile, species = [dbkey] )
            if index is None:
                print >> sys.stderr, "Your MAF file appears to be malformed."
                sys.exit()
        else: 
            print >>sys.stderr, "Desired source MAF type has not been specified."
            sys.exit()
    except Exception, exc:
        print >>sys.stdout, 'interval2maf.py initialization error -> %s' % exc
    
    out = bx.align.maf.Writer( open(output_file, "w") )
    
    # Iterate over input regions 
    num_blocks = 0
    num_lines = 0
    for num_lines, region in enumerate( bx.intervals.io.NiceReaderWrapper( open(interval_file, 'r' ), chrom_col = chromCol, start_col = startCol, end_col = endCol, strand_col = strandCol, fix_strand = True, return_header = False, return_comments = False ) ):
        try:
            src = "%s.%s" % ( dbkey, region.chrom )
            
            blocks = index.get( src, region.start, region.end )
            
            for block in blocks: 
                ref = block.get_component_by_src( src )
                #We want our block coordinates to be from positive strand
                if ref.strand == "-":
                    block = block.reverse_complement()
                    ref = block.get_component_by_src( src )
                
                #save old score here for later use
                old_score =  block.score
                slice_start = max( region.start, ref.start )
                slice_end = min( region.end, ref.end )
                
                #when interval is out-of-range (not in maf index), fail silently: else could create tons of scroll
                try:
                    block = block.slice_by_component( ref, slice_start, slice_end ) 
                except:
                    continue
                    
                if block.text_size > mincols:
                    if region.strand != ref.strand: block = block.reverse_complement()
                    # restore old score, may not be accurate, but it is better than 0 for everything
                    block.score = old_score
                    if species is not None:
                        block = block.limit_to_species( species )
                        block.remove_all_gap_columns()
                    out.write( block )
                    num_blocks += 1
        except Exception, e:
            print "Error found on input line %s: %s." % ( num_lines, e )
            continue
    
    # Close output MAF
    out.close()
    
    #remove index file if created during run
    if index_filename is not None:
        os.unlink( index_filename )
    
    print "%s MAF blocks extracted." % num_blocks
    
if __name__ == "__main__": __main__()
