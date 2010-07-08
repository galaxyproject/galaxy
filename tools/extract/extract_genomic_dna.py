#!/usr/bin/env python
"""
usage: %prog $input $out_file1
    -1, --cols=N,N,N,N: Columns for start, end, strand in input file
    -d, --dbkey=N: Genome build of input file
    -o, --output_format=N: the data type of the output file
    -g, --GALAXY_DATA_INDEX_DIR=N: the directory containing alignseq.loc
    -G, --gff: input and output file, when it is interval, coordinates are treated as GFF format (1-based, half-open) rather than 'traditional' 0-based, closed format.
"""
from galaxy import eggs
import pkg_resources
pkg_resources.require( "bx-python" )
import sys, string, os, re
from bx.cookbook import doc_optparse
import bx.seq.nib
import bx.seq.twobit
from galaxy.tools.util.galaxyops import *
from galaxy.tools.util.gff_util import *

assert sys.version_info[:2] >= ( 2, 4 )
    
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

def check_seq_file( dbkey, GALAXY_DATA_INDEX_DIR ):
    seq_file = "%s/alignseq.loc" % GALAXY_DATA_INDEX_DIR
    seq_path = ''
    for line in open( seq_file ):
        line = line.rstrip( '\r\n' )
        if line and not line.startswith( "#" ) and line.startswith( 'seq' ):
            fields = line.split( '\t' )
            if len( fields ) < 3:
                continue
            if fields[1] == dbkey:
                seq_path = fields[2].strip()
                break
    return seq_path

        
def __main__():
    options, args = doc_optparse.parse( __doc__ )
    try:
        chrom_col, start_col, end_col, strand_col = parse_cols_arg( options.cols )
        dbkey = options.dbkey
        output_format = options.output_format
        gff_format = options.gff
        GALAXY_DATA_INDEX_DIR = options.GALAXY_DATA_INDEX_DIR
        input_filename, output_filename = args
    except:
        doc_optparse.exception()

    includes_strand_col = strand_col >= 0
    strand = None
    nibs = {}
    twobits = {}
    seq_path = check_seq_file( dbkey, GALAXY_DATA_INDEX_DIR )
    if not os.path.exists( seq_path ):
        # If this occurs, we need to fix the metadata validator.
        stop_err( "No sequences are available for '%s', request them by reporting this error." % dbkey )

    skipped_lines = 0
    first_invalid_line = 0
    invalid_line = ''
    fout = open( output_filename, "w" )
    warnings = []
    warning = ''
    twobitfile = None
     
    for i, line in enumerate( open( input_filename ) ):
        line = line.rstrip( '\r\n' )
        if line and not line.startswith( "#" ):
            fields = line.split( '\t' )
            try:
                chrom = fields[chrom_col]
                start = int( fields[start_col] )
                end = int( fields[end_col] )
                if gff_format:
                    start, end = convert_gff_coords_to_bed( [start, end] )
                if includes_strand_col:
                    strand = fields[strand_col]
            except:
                warning = "Invalid chrom, start or end column values. "
                warnings.append( warning )
                skipped_lines += 1
                if not invalid_line:
                    first_invalid_line = i + 1
                    invalid_line = line
                continue
            if start > end:
                warning = "Invalid interval, start '%d' > end '%d'.  " % ( start, end )
                warnings.append( warning )
                skipped_lines += 1
                if not invalid_line:
                    first_invalid_line = i + 1
                    invalid_line = line
                continue

            if strand not in ['+', '-']:
                strand = '+'
            sequence = ''

            if seq_path and os.path.exists( "%s/%s.nib" % ( seq_path, chrom ) ):
                if chrom in nibs:
                    nib = nibs[chrom]
                else:
                    nibs[chrom] = nib = bx.seq.nib.NibFile( file( "%s/%s.nib" % ( seq_path, chrom ) ) )
                try:
                    sequence = nib.get( start, end-start )
                except:
                    warning = "Unable to fetch the sequence from '%d' to '%d' for build '%s'. " %( start, end-start, dbkey )
                    warnings.append( warning )
                    skipped_lines += 1
                    if not invalid_line:
                        first_invalid_line = i + 1
                        invalid_line = line
                    continue
            elif seq_path and os.path.isfile( seq_path ):
                if not(twobitfile):
                    twobitfile = bx.seq.twobit.TwoBitFile( file( seq_path ) )
                try:
                    sequence = twobitfile[chrom][start:end]
                except:
                    warning = "Unable to fetch the sequence from '%d' to '%d' for build '%s'. " %( start, end-start, dbkey )
                    warnings.append( warning )
                    skipped_lines += 1
                    if not invalid_line:
                        first_invalid_line = i + 1
                        invalid_line = line
                    continue
            else:
                warning = "Chromosome by name '%s' was not found for build '%s'. " % ( chrom, dbkey )
                warnings.append( warning )
                skipped_lines += 1
                if not invalid_line:
                    first_invalid_line = i + 1
                    invalid_line = line
                continue
            if sequence == '':
                warning = "Chrom: '%s', start: '%s', end: '%s' is either invalid or not present in build '%s'. " %( chrom, start, end, dbkey )
                warnings.append( warning )
                skipped_lines += 1
                if not invalid_line:
                    first_invalid_line = i + 1
                    invalid_line = line
                continue
            if includes_strand_col and strand == "-":
                sequence = reverse_complement( sequence )

            if output_format == "fasta" :
                l = len( sequence )        
                c = 0
                fields = [dbkey, str( chrom ), str( start ), str( end ), strand]
                meta_data = "_".join( fields )
                fout.write( ">%s\n" % meta_data )
                while c < l:
                    b = min( c + 50, l )
                    fout.write( "%s\n" % str( sequence[c:b] ) )
                    c = b
            else: # output_format == "interval"
                meta_data = "\t".join( fields )
                if gff_format:
                    format_str = "%s seq \"%s\";\n"
                else:
                    format_str = "%s\t%s\n"
                fout.write( format_str % ( meta_data, str( sequence ) ) )

    fout.close()

    if warnings:
        warn_msg = "%d warnings, 1st is: " % len( warnings )
        warn_msg += warnings[0]
        print warn_msg
    if skipped_lines:
        print 'Skipped %d invalid lines, 1st is #%d, "%s"' % ( skipped_lines, first_invalid_line, invalid_line )

if __name__ == "__main__": __main__()
