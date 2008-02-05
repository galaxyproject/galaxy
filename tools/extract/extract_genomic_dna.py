#!/usr/bin/env python2.4
"""
usage: extract_genomic_dna.py $input $out_file1 $input_chromCol $input_startCol $input_endCol $input_strandCol $dbkey $out_format
by Wen-Yu Chung
"""
import pkg_resources
pkg_resources.require( "bx-python" )
import sys, string, os, re
from bx.cookbook import doc_optparse
import bx.seq.nib
import bx.seq.twobit

nib_file = "/depot/data2/galaxy/alignseq.loc"
twobit_file = "/depot/data2/galaxy/twobit.loc"

def stop_err( msg ):
    sys.stderr.write( msg )
    sys.exit()

def reverse_complement( s ):
    complement_dna = {"A":"T", "T":"A", "C":"G", "G":"C", "a":"t", "t":"a", "c":"g", "g":"c", "N":"N", "n":"n" }
    reversed_s = []
    for i in s:
        reversed_s.append( complement_dna[i] )
    reversed_s.reverse()
    return "".join( reversed_s )

def check_nib_file( dbkey ):
    nib_path = ''
    nibs = {}
    for line in open( nib_file ):
        line = line.rstrip( '\r\n' )
        if line and not line.startswith( "#" ):
            fields = line.split()
            if len( fields ) < 3:
                continue
            if ( fields[0] == 'seq' ):
                nibs[( fields[1] )] = fields[2]
    if nibs.has_key( dbkey ):
        nib_path = nibs[( dbkey )]
    return nib_path

def check_twobit_file( dbkey ):
    twobit_path = ''
    twobits = {}
    for line in open( twobit_file ):
        line = line.rstrip( '\r\n' )
        if line and not line.startswith( "#" ): 
            fields = line.split()
            if len( fields ) < 2:
                continue
            twobits[( fields[0] )] = fields[1]
    if twobits.has_key( dbkey ):
        twobit_path = twobits[( dbkey )]
    return twobit_path
        
def __main__():
    input_filename = sys.argv[1]
    output_filename = sys.argv[2]
    includes_strand_col = False
    strand = None
    # If any of the following exceptions are thrown, we need to improve the metadata validator.
    try:
        chrom_col = int( sys.argv[3] ) - 1
    except:
        stop_err( "Chrom column not properly set, click the pencil icon in your history item to set it." )
    try:
        start_col = int( sys.argv[4] ) - 1
    except:
        stop_err( "Start column not properly set, click the pencil icon in your history item to set it." )
    try:
        end_col = int( sys.argv[5] ) - 1
    except:
        stop_err( "End column not properly set, click the pencil icon in your history item to set it." )
    try:
        strand_col = int( sys.argv[6] ) - 1
        if strand_col >= 0:
            includes_strand_col = True
    except:
        pass
    dbkey = sys.argv[7]
    output_format = sys.argv[8]

    # TODO: is this still necessary?  If so, let's get it fixed!
    if (re.search("^mm\d$", dbkey)):
        dbkey = "musMus" + dbkey[-1]
    if (re.search("^rn\d$", dbkey)):
        dbkey = "ratNor" + dbkey[-1]
    
    nibs = {}
    twobits = {}
    nib_path = check_nib_file( dbkey )
    twobit_path = check_twobit_file( dbkey )
    if not os.path.exists( nib_path ) and not os.path.exists( twobit_path ):
        # If this occurs, we need to fix the metadata validator.
        stop_err( "No sequences are available for %s, request them by reporting this error." % dbkey )

    skipped_lines = 0
    first_invalid_line = 0
    invalid_line = ''
    fout = open( output_filename, "w" )
    err_msg = ''

    for i, line in enumerate( open( input_filename ) ):
        line = line.rstrip( '\r\n' )
        if line and not line.startswith( "#" ):
            fields = line.split( '\t' )
            try:
                chrom = fields[chrom_col]
                start = int( fields[start_col] )
                end = int( fields[end_col] )
                if includes_strand_col:
                    strand = fields[strand_col]
                if strand not in ['+', '-']:
                    strand = "+"
    
                sequence = ''
                if os.path.exists( "%s/%s.nib" % ( nib_path, chrom) ):
                    if chrom in nibs:
                        nib = nibs[chrom]
                    else:
                        nibs[chrom] = nib = bx.seq.nib.NibFile( file( "%s/%s.nib" % ( nib_path, chrom ) ) )
                    try:
                        sequence = nib.get( start, end-start )
                    except:
                        err_msg = "Unable to fetch the sequence from %d to %d from %s." %( start, end-start, nib_path )
                        break
                elif os.path.exists( twobit_path ):
                    if chrom in twobits:
                        t = twobits[chrom]
                    else:
                        twobits[chrom] = t = bx.seq.twobit.TwoBitFile( file( twobit_path ) )
                    try:
                        sequence = t[chrom][start:end]
                    except:
                        err_msg = "Unable to fetch the sequence from %d to %d from %s." %( start, end-start, twobit_path )
                        break
                else:
                    err_msg = "Sequence %s was not found for build %s.  Most likely your data lists the wrong chromosome number for this organism. Check your build selection." % ( chrom, dbkey )
                    break
    
                if not sequence:
                    err_msg = "%s_%s_%s is either invalid or not present in the specified build." %( chrom, start, end )
                    break
                if includes_strand_col and strand == "-":
                    sequence = reverse_complement( sequence )
    
                if output_format == "fasta" :
                    l = len( sequence )        
                    c = 0
                    fields = [dbkey, str( chrom ), str( start ), str( end ), strand]
                    meta_data = "_".join( fields )
                    print >> fout, ">%s" %meta_data
                    while c < l:
                        b = min( c + 50, l )
                        print >> fout, sequence[c:b]
                        c = b
                else: # output_format == "interval"
                    meta_data = "\t".join( fields )
                    print >> fout, meta_data, "\t", sequence
            except:
                skipped_lines += 1
                if not invalid_line:
                    first_invalid_line = i + 1
                    invalid_line = line
    fout.close()
    if err_msg:
        stop_err( err_msg )
    if skipped_lines:
        print 'Data issue: skipped %d invalid lines starting at line #%d, "%s"' % ( skipped_lines, first_invalid_line, invalid_line )

if __name__ == "__main__": __main__()