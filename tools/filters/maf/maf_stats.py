#!/usr/bin/env python2.4
#Dan Blankenberg
"""
Reads a list of intervals and a maf. Outputs a new set of intervals with statistics appended.
"""

import sys, tempfile, os
import pkg_resources; pkg_resources.require( "bx-python" )
import bx.align
import bx.align.maf
import bx.intervals.io
import bx.interval_index_file
import psyco_full

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
    for region in bx.intervals.io.NiceReaderWrapper( open( input_interval_filename, 'r' ), chrom_col = chr_col, start_col = start_col, end_col = end_col, fix_strand = True, return_header = False, return_comments = False ):
        sequences = {dbkey: [ False for i in range( region.end - region.start ) ]}
        
        src = dbkey + "." + region.chrom
        start = region.start
        end = region.end
        
        total_length += (end - start)
        
        blocks = index.get( src, start, end )
        for maf in blocks:
            #make sure all species are known
            for c in maf.components:
                spec = c.src.split( '.' )[0]
                if spec not in sequences: sequences[spec] = [ False for i in range( region.end - region.start ) ]
            
            #save old score here for later use, since slice results score==0
            old_score =  maf.score
            
            #slice maf by start and end
            ref = maf.get_component_by_src( bx.align.src_merge( dbkey, region.chrom ) )
            # If the reference component is on the '-' strand we should complement the interval
            if ref.strand == '-':
                slice_start = max( ref.src_size - end, ref.start )
                slice_end = max( ref.src_size - start, ref.end )
            else:
                slice_start = max( start, ref.start )
                slice_end = min( end, ref.end )
            try:
                sliced = maf.slice_by_component( ref, slice_start, slice_end )
            except:
                #print "slicing failed!"
                continue
            ref = sliced.get_component_by_src( ref.src )
            #look for gaps (indels) in primary sequence, we do not include these columns in our stats
            gaps = []
            for i in range( len( ref.text ) ):
                if ref.text[i] in ['-']:
                    gaps.append( i )
            
            #Set nucleotide containing columns
            for c in sliced.components:
                spec = c.src.split( '.' )[0]
                gap_offset = 0
                for i in range( len( c.text ) ):
                    if i in gaps: gap_offset += 1
                    elif c.text[i] not in ['-']: sequences[spec][i - gap_offset + slice_start - start] = True
            
        if summary:
            #record summary
            for key in sequences.keys():
                if key not in species_summary: species_summary[key] = 0
                species_summary[key] = species_summary[key] + sequences[key].count( True )
        else:
            #print sequences
            out.write( "%s\t%s\t%s\t%s\n" % ( "\t".join( region.fields ), dbkey, sequences[dbkey].count( True ), sequences[dbkey].count( False ) ) )
            keys = sequences.keys()
            keys.remove( dbkey )
            keys.sort()
            for key in keys:
                out.write( "%s\t%s\t%s\t%s\n" % ( "\t".join( region.fields ), key, sequences[key].count( True ), sequences[key].count( False ) ) )
        num_region += 1
    if summary:
        out.write( "#species\tnucleotides\tcoverage\n" )
        for spec in species_summary:
            out.write( "%s\t%s\t%.4f\n" % ( spec, species_summary[spec], float( species_summary[spec] ) / total_length ) )
    print "%i regions were processed with a total length of %i." % ( num_region, total_length )
    out.close()
    if index_filename is not None:
        os.unlink( index_filename )
if __name__ == "__main__": __main__()
