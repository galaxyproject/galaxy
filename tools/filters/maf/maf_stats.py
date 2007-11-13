#!/usr/bin/env python2.4
#Dan Blankenberg
"""
Reads a list of intervals and a maf. Outputs a new set of intervals with statistics appended.
"""

import sys, tempfile, os
import pkg_resources; pkg_resources.require( "bx-python" )
import bx.align.maf
import bx.intervals.io
import bx.interval_index_file
import psyco_full
from numpy import zeros

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


def __main__():
    maf_source_type = sys.argv.pop( 1 )
    input_maf_filename = sys.argv[1].strip()
    input_interval_filename = sys.argv[2].strip()
    output_filename = sys.argv[3].strip()
    dbkey = sys.argv[4].strip()
    try:
        chr_col  = int( sys.argv[5].strip() ) - 1
        start_col = int( sys.argv[6].strip() ) - 1
        end_col = int( sys.argv[7].strip() ) - 1
    except:
        print >>sys.stderr, "You appear to be missing metadata. You can specify your metadata by clicking on the pencil icon associated with your interval file."
        sys.exit()
    summary = sys.argv[8].strip()
    if summary.lower() == "true": summary = True
    else: summary = False
    
    index = index_filename = None
    if maf_source_type == "user":
        #index maf for use here
        index, index_filename = build_maf_index( input_maf_filename, species = [dbkey] )
        if index is None:
            print >>sys.stderr, "Your MAF file appears to be malformed."
            sys.exit()
    elif maf_source_type == "cached":
        #access existing indexes
        index = maf_index_by_uid( input_maf_filename )
        if index is None:
            print >> sys.stderr, "The MAF source specified (%s) appears to be invalid." % ( input_maf_filename )
            sys.exit()
    else:
        print >>sys.stdout, 'Invalid source type specified: %s' % maf_source_type 
        sys.exit()
        
    out = open(output_filename, 'w')
    
    num_region = 0
    species_summary = {}
    total_length = 0
    #loop through interval file
    for num_region, region in enumerate( bx.intervals.io.NiceReaderWrapper( open( input_interval_filename, 'r' ), chrom_col = chr_col, start_col = start_col, end_col = end_col, fix_strand = True, return_header = False, return_comments = False ) ):
        src = "%s.%s" % ( dbkey, region.chrom )
        total_length += ( region.end - region.start )
        coverage = { dbkey: zeros( region.end - region.start, dtype = bool ) }
        
        blocks = index.get( src, region.start, region.end )
        for maf in blocks:
            #make sure all species are known
            for c in maf.components:
                spec = c.src.split( '.' )[0]
                if spec not in coverage: coverage[spec] = zeros( region.end - region.start, dtype = bool )
            #slice maf by start and end
            ref = maf.get_component_by_src( src )
            # If the reference component is on the '-' strand we should complement the interval
            if ref.strand == '-':
                maf = maf.reverse_complement()
                ref = maf.get_component_by_src( src )
            slice_start = max( region.start, ref.start )
            slice_end = min( region.end, ref.end )
            try:
                maf = maf.slice_by_component( ref, slice_start, slice_end )
            except:
                continue
            ref = maf.get_component_by_src( ref.src )
            
            #skip gap locations due to insertions in secondary species relative to primary species
            start_offset = slice_start - region.start
            num_gaps = 0
            for i in range( len( ref.text.rstrip().rstrip( "-" ) ) ):
                if ref.text[i] in ["-"]:
                    num_gaps += 1
                    continue
                #Toggle base if covered
                for comp in maf.components:
                    spec = comp.src.split( '.' )[0]
                    if comp.text and comp.text[i] not in ['-']:
                        coverage[spec][start_offset + i - num_gaps] = True
        if summary:
            #record summary
            for key in coverage.keys():
                if key not in species_summary: species_summary[key] = 0
                species_summary[key] = species_summary[key] + sum( coverage[key] )
        else:
            #print coverage for interval
            out.write( "%s\t%s\t%s\t%s\n" % ( "\t".join( region.fields ), dbkey, sum( coverage[dbkey] ), len(coverage[dbkey]) - sum( coverage[dbkey] ) ) )
            keys = coverage.keys()
            keys.remove( dbkey )
            keys.sort()
            for key in keys:
                out.write( "%s\t%s\t%s\t%s\n" % ( "\t".join( region.fields ), key, sum( coverage[key] ), len(coverage[key]) - sum( coverage[key] ) ) )
    if summary:
        out.write( "#species\tnucleotides\tcoverage\n" )
        for spec in species_summary:
            out.write( "%s\t%s\t%.4f\n" % ( spec, species_summary[spec], float( species_summary[spec] ) / total_length ) )
    out.close()
    print "%i regions were processed with a total length of %i." % ( num_region, total_length )
    if index_filename is not None:
        os.unlink( index_filename )
if __name__ == "__main__": __main__()
