#!/usr/bin/env python

"""
Runs Lastz paired read alignment process
Written for Lastz v. 1.02.00.

# Author(s): based on various scripts written by Bob Harris (rsharris@bx.psu.edu),
# then tweaked to this form by Greg Von Kuster (greg@bx.psu.edu)

This tool takes the following input:
a. A collection of 454 paired end reads ( a fasta file )
b. A linker sequence ( a very small fasta file )
c. A reference genome ( nob, 2bit or fasta )

and uses the following process:
1. Split reads into mates:  the input to this step is the read file XXX.fasta, and the output is three
   files; XXX.short.fasta, XXX.long.fasta and XXX.mapping.  The mapping file records the information necessary
   to convert mate coordinates back into the original read, which is needed later in the process.

2. Align short mates to the reference: this runs lastz against every chromosome.  The input is XXX.short.fasta
   and the reference genome, and the output is a SAM file, XXX.short.sam.

3. Align long mates to the reference: this runs lastz against every chromosome.  The input is XXX.long.fasta
   and the reference genome, and the output is a SAM file, XXX.long.sam.

4. Combine, and convert mate coordinates back to read coordinates.  The input is XXX.mapping, XXX.short.sam and
   XXX.long.sam, and the output is XXX.sam.

usage: lastz_paired_reads_wrapper.py [options]
    --ref_name: The reference name to change all output matches to
    --ref_source: The reference is cached or from the history
    --source_select: Use pre-set or cached reference file
    --input1: The name of the reference file if using history or reference base name if using cached
    --input2: The reads file to align
    --input3: The sequencing linker file
    --input4: The base quality score 454 file
    --ref_sequences: The number of sequences in the reference file if using one from history 
    --output: The name of the output file
    --lastz_seqs_file_dir: Directory of local lastz_seqs.loc file
"""
import optparse, os, subprocess, shutil, sys, tempfile, time
from string import maketrans

from galaxy import eggs
import pkg_resources
pkg_resources.require( 'bx-python' )
from bx.seq.twobit import *
from bx.seq.fasta import FastaReader
from galaxy.util.bunch import Bunch
from galaxy.util import string_as_bool

# Column indexes for SAM required fields
SAM_QNAME_COLUMN = 0
SAM_FLAG_COLUMN  = 1
SAM_RNAME_COLUMN = 2
SAM_POS_COLUMN   = 3
SAM_MAPQ_COLUMN  = 4
SAM_CIGAR_COLUMN = 5
SAM_MRNM_COLUMN  = 6
SAM_MPOS_COLUMN  = 7
SAM_ISIZE_COLUMN = 8
SAM_SEQ_COLUMN   = 9
SAM_QUAL_COLUMN  = 10
SAM_MIN_COLUMNS  = 11
# SAM bit-encoded flags
BAM_FPAIRED      =    1    # the read is paired in sequencing, no matter whether it is mapped in a pair
BAM_FPROPER_PAIR =    2    # the read is mapped in a proper pair
BAM_FUNMAP       =    4    # the read itself is unmapped; conflictive with BAM_FPROPER_PAIR
BAM_FMUNMAP      =    8    # the mate is unmapped
BAM_FREVERSE     =   16    # the read is mapped to the reverse strand
BAM_FMREVERSE    =   32    # the mate is mapped to the reverse strand
BAM_FREAD1       =   64    # this is read1
BAM_FREAD2       =  128    # this is read2
BAM_FSECONDARY   =  256    # not primary alignment
BAM_FQCFAIL      =  512    # QC failure
BAM_FDUP         = 1024    # optical or PCR duplicate

# Keep track of all created temporary files so they can be deleted
global tmp_file_names
tmp_file_names = []
# The values in the skipped_lines dict are tuples consisting of:
# - the number of skipped lines for that error
# If not a sequence error:
# - the 1st line number on which the error was found
# - the text of the 1st line on which the error was found
# If a sequence error:
# - The number of the sequence in the file
# - the sequence name on which the error occurred
# We may need to improve dealing with file position and text as
# much of it comes from temporary files that are created from the
# inputs, and not the inputs themselves, so this could be confusing
# to the user.
global skipped_lines
skipped_lines = dict( bad_interval=( 0, 0, '' ),
                      inconsistent_read_lengths=( 0, 0, '' ),
                      inconsistent_reads=( 0, 0, '' ),
                      inconsistent_sizes=( 0, 0, '' ),
                      missing_mate=( 0, 0, '' ),
                      missing_quals=( 0, 0, '' ),
                      missing_seq=( 0, 0, '' ),
                      multiple_seqs=( 0, 0, '' ),
                      no_header=( 0, 0, '' ),
                      num_fields=( 0, 0, '' ),
                      reads_paired=( 0, 0, '' ),
                      sam_flag=( 0, 0, '' ),
                      sam_headers=( 0, 0, '' ),
                      sam_min_columns=( 0, 0, '' ),
                      two_mate_names=( 0, 0, '' ),
                      wrong_seq_len=( 0, 0, '' ) )
global total_skipped_lines
total_skipped_lines = 0

def stop_err( msg ):
    sys.stderr.write( "%s" % msg )
    sys.exit()

def skip_line( error_key, position, text ):
    if not skipped_lines[ error_key ][2]:
        skipped_lines[ error_key ][1] = position
        skipped_lines[ error_key ][2] = text
    skipped_lines[ error_key ][0] += 1
    total_skipped_lines += 1

def get_tmp_file_name( dir=None, suffix=None ):
    """
    Return a unique temporary file name that can be managed.  The
    file must be manually removed after use.
    """
    if dir and suffix:
        tmp_fd, tmp_name = tempfile.mkstemp( dir=dir, suffix=suffix )
    elif dir:
        tmp_fd, tmp_name = tempfile.mkstemp( dir=dir )
    elif suffix:
        tmp_fd, tmp_name = tempfile.mkstemp( suffix=suffix )
    os.close( tmp_fd )
    tmp_file_names.append( tmp_name )
    return tmp_name

def run_command( command ):
    proc = subprocess.Popen( args=command, shell=True, stderr=subprocess.PIPE, )
    proc.wait()
    stderr = proc.stderr.read()
    proc.wait()
    if stderr:
        stop_err( stderr )

def split_paired_reads( input2, combined_linker_file_name ):
    """
    Given a fasta file of allegedly paired end reads ( input2 ), and a list of intervals
    showing where the linker is on each read ( combined_linker_file_name ), split the reads into left and right
    halves.
    
    The input intervals look like this.  Note that they may include multiple intervals for the same read
    ( which should overlap ), and we use the union of them as the linker interval.  Non-overlaps are
    reported to the user, and those reads are not processed.  Starts are origin zero.
    
        #name     strand start len size
        FG3OYDA05FTEES +   219  42 283
        FG3OYDA05FVOLL +   263  41 416
        FG3OYDA05FFL7J +    81  42 421
        FG3OYDA05FOQWE +    55  42 332
        FG3OYDA05FV4DW +   297  42 388
        FG3OYDA05FWAQV +   325  42 419
        FG3OYDA05FVLGA +    90  42 367
        FG3OYDA05FWJ71 +    58  42 276
    
    The output gives each half-sequence on a separate line, like this.  This allows easy sorting of the
    sequences by length, after the fact.
    
        219 FG3OYDA05FTEES_L TTTAGTTACACTTAACTCACTTCCATCCTCTAAATACGTGATTACCTTTC...
        22  FG3OYDA05FTEES_R CCTTCCTTAAGTCCTAAAACTG
    """
    # Bob says these should be hard-coded.
    seq_len_lower_threshold = 17
    short_mate_cutoff = 50
    # We need to pass the name of this file back to the caller.
    tmp_mates_file_name = get_tmp_file_name( suffix='mates.txt' )
    mates_file = file( tmp_mates_file_name, "w+b" )
    # Read the linker intervals
    combined_linker_file = file( combined_linker_file_name, "rb" )
    read_to_linker_dict = {}
    i = 0
    for i, line in enumerate( combined_linker_file ):
        line = line.strip()
        if line.startswith( "#" ):
            continue
        if line.find( '#' ) >= 0:
            line = line.split( "#", 1 )[0].rstrip()
        fields = line.split()
        if len( fields ) != 4:
            skip_line( 'num_fields', i+1, line )
            continue
        name, start, length, size = fields
        start = int( start )
        length = int( length )
        size = int( size )
        end = start + length
        if end > size:
            skip_line[ 'bad_interval' ] += 1
            continue
        if name not in read_to_linker_dict:
            read_to_linker_dict[ name ] = ( start, end, size )
            continue
        if read_to_linker_dict[ name ] == None:
            # Read previously marked as non-overlapping intervals, so skip this sequence - see below
            continue
        ( s, e, sz ) = read_to_linker_dict[ name ]
        if sz != size:
            skip_line( 'inconsistent_sizes', i+1, name )
            continue
        if s > end or e < start:
            # Non-overlapping intervals, so skip this sequence
            read_to_linker_dict[ name ] = None
            continue
        read_to_linker_dict[ name ] = ( min( s, start ), max( e, end ), size )
    combined_linker_file.close()
    # We need to pass the name of this file back to the caller.
    tmp_mates_mapping_file_name = get_tmp_file_name( suffix='mates.mapping' )
    mates_mapping_file = file( tmp_mates_mapping_file_name, 'w+b' )
    # Process the sequences
    seqs = 0
    fasta_reader = FastaReader( file( input2, 'rb' ) )
    while True:
        seq = fasta_reader.next()
        if not seq:
            break
        seqs += 1
        if seq.name not in read_to_linker_dict:
            if seq.length > seq_len_lower_threshold:
                mates_file.write( "%-3d %s   %s\n" % ( seq.length, seq.name, seq.text ) )
            read_to_linker_dict[ seq.name ] = ""
            continue
        if read_to_linker_dict[ seq.name ] == "":
            skip_line( 'multiple_seqs', seqs, seq.name )
            continue
        if read_to_linker_dict[ seq.name ] == None:
            # Read previously marked as non-overlapping intervals, so skip this sequence - see above
            continue
        ( start, end, size ) = read_to_linker_dict[ seq.name ]
        if seq.length != size:
            skip_line( 'wrong_seq_len', seqs, seq.name )
            continue
        left = seq.text[ :start ]
        right = seq.text[ end: ]
        left_is_small = len( left ) <= seq_len_lower_threshold
        right_is_small = len( right ) <= seq_len_lower_threshold
        if left_is_small and right_is_small:
            continue
        if not left_is_small:
            mates_file.write( "%-3d %s %s\n" % ( len( left ), seq.name + "_L", left ) )
            mates_mapping_file.write( "%s %s %s %s\n" % ( seq.name + "_L", seq.name, 0, size - start ) )
        if not right_is_small:
            mates_file.write( "%-3d %s %s\n" % ( len( right ), seq.name + "_R", right ) )
            mates_mapping_file.write( "%s %s %s %s\n" % ( seq.name + "_R", seq.name, end, 0 ) )
        read_to_linker_dict[ seq.name ] = ""
    combined_linker_file.close()
    mates_file.close()
    mates_mapping_file.close()
    # Create temporary files for short and long mates
    tmp_mates_short_file_name = get_tmp_file_name( suffix='mates.short' )
    tmp_mates_long_file_name = get_tmp_file_name( suffix='mates.long' )
    tmp_mates_short = open( tmp_mates_short_file_name, 'w+b' )
    tmp_mates_long = open( tmp_mates_long_file_name, 'w+b' )
    i = 0
    for i, line in enumerate( file( tmp_mates_file_name, 'rb' ) ):
        fields = line.split()
        seq_len = int( fields[0] )
        seq_name = fields[1]
        seq_text = fields[2]
        if seq_len <= short_mate_cutoff:
            tmp_mates_short.write( ">%s\n%s\n" % ( seq_name, seq_text ) )
        else:
            tmp_mates_long.write( ">%s\n%s\n" % ( seq_name, seq_text ) )
    tmp_mates_short.close()
    tmp_mates_long.close()
    return tmp_mates_mapping_file_name, tmp_mates_file_name, tmp_mates_short_file_name, tmp_mates_long_file_name

def align_mates( input1, ref_source, ref_name, ref_sequences, tmp_mates_short_file_name, tmp_mates_long_file_name ):
    tmp_align_file_names = []
    if ref_source == 'history':
        # Reference is a fasta dataset from the history
        # Create temporary files to contain the output from lastz executions
        tmp_short_file_name = get_tmp_file_name( suffix='short_out' )
        tmp_align_file_names.append( tmp_short_file_name )
        tmp_long_file_name = get_tmp_file_name( suffix='long_out' )
        tmp_align_file_names.append( tmp_long_file_name )
        seqs = 0
        fasta_reader = FastaReader( open( input1 ) )
        while True:
            # Read the next sequence from the reference dataset.  Note that if the reference contains
            # a small number of chromosomes this loop is ok, but in many cases the genome has a bunch
            # of small straggler scaffolds and contigs and it is a computational waste to do each one
            # of these in its own run.  There is an I/O down side to running by subsets (even if they are
            # one sequence per subset), compared to splitting the reference into sizes of 250 mb.  With
            # the subset action, lastz still has to read and parse the entire file for every run (this
            # is true for fasta, but for .2bit files it can access each sequence directly within the file,
            # so the overhead is minimal).
            """
            :> output_file  (this creates the output file, empty)
            while there are more sequences to align
                find the next sequences that add up to 250M, put their names in farf.names
                lastz ${refFile}[subset=farf.names][multi][unmask] ${matesPath}/${matesFile} ... 
                  >> output_file
            """
            seq = fasta_reader.next()
            if not seq:
                break
            seqs += 1
            # Create a temporary file to contain the current sequence as input to lastz.
            # We're doing this a bit differently here since we could be generating a huge
            # number of temporary files.
            tmp_in_fd, tmp_in_file_name = tempfile.mkstemp( suffix='seq_%d_in' % seqs )
            tmp_in_file = os.fdopen( tmp_in_fd, 'w+b' )
            tmp_in_file.write( '>%s\n%s\n' % ( seq.name, seq.text ) )
            tmp_in_file.close()
            # Align short mates
            command = 'lastz %s[unmask]%s %s ' % ( tmp_in_file_name, ref_name, tmp_mates_short_file_name )
            command += 'Z=1 --seed=1111111011111 --notrans --maxwordcount=90% --match=1,3 O=1 E=3 X=15 K=10 Y=12 L=18 --ambiguousn --noytrim --identity=95 --coverage=80 --continuity=95 --format=softsam- '
            command += '>> %s' % tmp_short_file_name
            run_command( command )
            # Align long mates
            command = 'lastz %s[unmask]%s %s ' % ( tmp_in_file_name, ref_name, tmp_mates_long_file_name )
            command += 'Z=15 W=13 --notrans --exact=18 --maxwordcount=90% --match=1,3 O=1 E=3 Y=10 L=18 --ambiguousn --noytrim --identity=95 --coverage=90 --continuity=95 --format=softsam- '
            command += '>> %s' % tmp_long_file_name
            run_command( command )
            # Remove the temporary file that contains the current sequence
            os.remove( tmp_in_file_name )
    else:
        # Reference is a locally cached 2bit file, split lastz calls across number of chroms in 2bit file
        tbf = TwoBitFile( open( input1, 'rb' ) )
        for chrom in tbf.keys():
            # Align short mates
            tmp_short_file_name = get_tmp_file_name( suffix='short_vs_%s' % chrom )
            tmp_align_file_names.append( tmp_short_file_name )
            command = 'lastz %s/%s[unmask]%s %s ' % ( input1, chrom, ref_name, tmp_mates_short_file_name )
            command += 'Z=1 --seed=1111111011111 --notrans --maxwordcount=90% --match=1,3 O=1 E=3 X=15 K=10 Y=12 L=18 --ambiguousn --noytrim --identity=95 --coverage=80 --continuity=95 --format=softsam- '
            command += '> %s' % tmp_short_file_name
            run_command( command )
            # Align long mates
            tmp_long_file_name = get_tmp_file_name( suffix='long_vs_%s' % chrom )
            tmp_align_file_names.append( tmp_long_file_name )
            command = 'lastz %s/%s[unmask]%s %s ' % ( input1, chrom, ref_name, tmp_mates_long_file_name )
            command += 'Z=15 W=13 --notrans --exact=18 --maxwordcount=90% --match=1,3 O=1 E=3 Y=10 L=18 --ambiguousn --noytrim --identity=95 --coverage=90 --continuity=95 --format=softsam- '
            command += '> %s' % tmp_long_file_name
            run_command( command )
    return tmp_align_file_names

def paired_mate_unmapper( input2, input4, tmp_mates_mapping_file_name, tmp_align_file_name_list, output ):
    """
    Given a SAM file corresponding to alignments of *subsegments* of paired 'reads' to a reference sequence,
    convert the positions on the subsegments to positions on the reads.  Also (optionally) add quality values.
    
    The input file is in SAM format, as shown below.  Each line represents the alignment of a part of a read
    to a reference sequence.  Read pairs are indicated by suffixes in their names.  Normally, the suffixes _L
    and _R indicate the left and right mates of reads (this can be overridden with the --left and --right
    options).  Reads that were not mates have no suffix.
    
        (SAM header lines omitted)
        F2YP0BU02G7LK5_R 16 chr21 15557360 255 40M          * 0 0 ATTTTATTCTCTTTGAAGCAATTGTGAATGGGAGTTTACT           *
        F2YP0BU02HXV58_L 16 chr21 15952091 255 40M6S        * 0 0 GCAAATTGTGCTGCTTTAAACATGCGTGTGCAAGTATCTTtttcat     *
        F2YP0BU02HREML_R 0  chr21 16386077 255 33M5S        * 0 0 CCAAAGTTCTGGGATTACAGGCGTGAGCCATCGcgccc             *
        F2YP0BU02IOF1F_L 0  chr21 17567321 255 7S28M        * 0 0 taaagagAAGAATTCTCAACCCAGAATTTCATATC                *
        F2YP0BU02IKX84_R 16 chr21 18491628 255 22M1D18M9S   * 0 0 GTCTCTACCAAAAAATACAAAAATTAGCCGGGCGTGGTGGcatgtctgt  *
        F2YP0BU02GW5VA_L 16 chr21 20255344 255 6S32M        * 0 0 caagaaCAAACACATTCAAAAGCTAGTAGAAGGCAAGA             *
        F2YP0BU02JIMJ4_R 0  chr21 22383051 255 19M          * 0 0 CCCTTTATCATTTTTTATT                                *
        F2YP0BU02IXZGF_L 16 chr21 23094798 255 13M1I18M     * 0 0 GCAAGCTCCACTTCCCGGGTTCACGCCATTCT                   *
        F2YP0BU02IODR5_L 0  chr21 30935325 255 37M          * 0 0 GAAATAAAGGGTATTCAATTAGGAAAAGAGGAAGTCA              *
        F2YP0BU02IMZBL_L 16 chr21 31603486 255 28M1D1M      * 0 0 ATACAAAAATTAGCCGGGCACAGTGGCAG                      *
        F2YP0BU02JA9PR_L 16 chr21 31677159 255 23M          * 0 0 CACACCTGTAACCCCAGCACTTT                            *
        F2YP0BU02HKC61_R 0  chr21 31678718 255 40M          * 0 0 CACTGCACTCCAGCCTGGGTGACAAAGCAAGACTCTGTCT           *
        F2YP0BU02HKC61_R 0  chr21 31678718 255 40M          * 0 0 CACTGCACTCCAGCCTGGGTGACAAAGCAAGACTCTGTCT           *
        F2YP0BU02HVA88   16 chr21 31703558 255 1M1D35M8S    * 0 0 TGGGATTACAGGCGTGAGCTACCACACCCAGCCAGAgttcaaat       *
        F2YP0BU02JDCF1_L 0  chr21 31816600 255 38M          * 0 0 AGGAGAATCGCTTGAACCCAGGAGGCAGAGGTTGCGGT             *
        F2YP0BU02GZ1GO_R 0  chr21 33360122 255 6S38M        * 0 0 cctagaCTTCACACACACACACACACACACACACACACACACAC       *
        F2YP0BU02FX387_L 16 chr22 14786201 255 26M          * 0 0 TGGATGAAGCTGGAAACCATCATTCT                         *
        F2YP0BU02IF2NE_R 0  chr22 16960842 255 40M10S       * 0 0 TGGCATGCACCTGTAGTCTCAGCTACTTGGGAGGCTGAGGtgggaggatc *
        F2YP0BU02F4TVA   0  chr22 19200522 255 49M          * 0 0 CCTGGGAGGCGGAGGTTGCAGTGAGCCGAGATCACGCCATTGCACTCCA  *
        F2YP0BU02HKC61_R 16 chr22 29516998 255 8S32M        * 0 0 agacagagTCTTGCTTTGTCACCCAGGCTGGAGTGCAGTG           *
        F2YP0BU02FS4EM_R 0  chr22 30159364 255 29M          * 0 0 CTCCTGCCTCAGCCTCCCGAGTAGTTGGG                      *
        F2YP0BU02G197P_L 0  chr22 32044496 255 40M10S       * 0 0 TTGTTGGACATTTGGGTTGGTTCCAAGTCTTTGCTATTGTgaataatgcc *
        F2YP0BU02FIING   16 chr22 45959944 255 3M1I11M1I26M * 0 0 AGCTATGGTACTGGCTATGAAAGCAGACACATAGACCAATGG         *
        F2YP0BU02GUB9L_L 16 chr22 49198404 255 16M1I20M     * 0 0 CACCACGCTCGGCTAATTTTTGTATTTTTAGTAGAGA              *
    
    The user must provide a mapping file (which might better be called an unmapping file).  This file is usually
    created by split_paired_reads, and tells us how to map the subsegments back to original coordinates in a single
    read (this means the left and right mates were part of a single read).  The mapping file contains four columns.
    The first two give the mates's name (including the suffix) and the read name.  The last two columns describe how
    much of the full original sequence is missing from the mate.  For example, in the read below, the left mate is
    missing 63 on the right (42 for the linker and 21 for the right half).  The right mate is missing 339 on the left.
    
        left half:  TTTCAACATATGCAAATCAATAAATGTAATCCAGCATATAAACAGAACCA
                    AAGACAAAAACCACATGATTATCTCAATAGATGCAGAAAAGGCCTTCGGC
                    AAAATTCAACAAAACTCCATGCTAAAACTCTCAATAAGGTATTGATGGGA
                    CATGCCGCATAATAATAAGACATATCTATGACAAACCCACAGCCAATATC
                    ATGCTGAATGCACAAAAATTGGAAGCATTCCCTTTGAAAACTGGCACAAG
                    ACTGGGATGCCCTCTCTCACAACTCCTATTCAACATAGTGTTGGAAG
        linker:     CGTAATAACTTCGTATAGCATACATTATACGAAGTCATACGA
        right half: CTCCTGCCTCAGCCTCCCGAG
    
        mate_name        read_name      offset_to_start offset_from_end
        F2YP0BU02FS4EM_L F2YP0BU02FS4EM         0              71
        F2YP0BU02FS4EM_R F2YP0BU02FS4EM       339               0
    
    The user can also specify a quality scores file, which should look something like this.  Quality values are presumed
    to be PHRED scores, written in space-delimited decimal.
    
        >F2YP0BU02FS4EM
        38 38 38 40 40 40 40 40 40 40 40 40 40 39 39 39 40 40 40 40 38 21 21 21 40
        40 40 40 40 40 40 40 40 40 40 40 40 40 40 39 39 39 40 40 40 40 40 40 40 33
        32 32 40 40 40 21 21 18 18 21 34 34 31 40 40 40 40 40 40 40 40 40 40 40 40
        40 40 40 40 40 40 40 40 40 40 40 32 32 32 32 40 40 40 40 40 40 40 34 34 35
        31 31 28 28 33 33 33 36 36 36 17 17 17 19 26 36 36 36 40 40 40 40 40 33 34
        34 34 39 39 39 40 40 40 40 40 33 33 34 34 40 40 40 40 40 40 40 39 39 39 40
        40 40 40 40 40 40 40 40 40 40 40 40 40 40 40 40 40 40 40 40 40 40 40 40 40
        40 40 40 40 40 40 40 39 39 39 39 39 39 40 40 40 39 39 39 40 40 40 40 40 40
        40 40 40 40 40 40 40 40 40 40 40 40 40 26 26 26 26 26 40 40 38 38 37 35 33
        36 40 19 17 17 17 17 19 19 23 30 20 20 20 23 35 40 36 36 36 36 36 36 36 36
        39 40 34 20 27 27 35 39 40 37 40 40 40 40 40 40 40 40 40 40 34 34 35 39 40
        40 40 40 40 40 40 39 39 39 40 40 40 40 36 36 32 32 28 28 29 30 36 40 30 26
        26 26 34 39 40 40 40 40 40 40 40 40 40 40 40 40 40 40 40 40 40 40 39 39 39
        40 39 35 34 34 40 40 40 40 30 30 30 35 40 40 40 40 40 39 39 36 40 40 40 40
        39 39 39 39 30 30 28 35 35 39 40 40 40 40 40 35 35 35
        >F2YP0BU02G197P
        40 40 40 40 40 40 40 40 40 40 39 39 39 39 39 39 40 40 40 40 40 40 40 40 40
        40 40 40 40 26 26 26 40 40 40 40 40 40 40 40 40 40 40 40 40 40 40 40 40 40
        40 40 40 40 40 40 40 40 40 40 40 40 40 40 40 40 40 40 40 40 40 40 40 40 40
        40 40 40 40 40 40 40 40 40 40 40 40 40 40 40 40 40 40 40 40 40 40 40 40 40
        40 40 40 40 40 40 40 40 40 40 40 40 40 40 40 40 40 40 40 40 34 34 34 40 40
        40 40 40 40 40 40 39 39 39 40 40 40 40 40 40 40 40 40 40 39 39 39 40 40 40
        40 40 40 40 40 40 40 34 34 34 34 40 40 40 40 34 34 34 34 40 40 40 40 40 40
        40 40 40 40 40 39 39 39 34 34 34 34 40 40 40 40 39 39 25 25 26 39 40 40 40
        40 40 40 40 40 40 40 40 40 40 40 40 40 40 40 40 40 40 40 40 40 40 40 40 40
        33 33 33 33 40 35 21 21 21 30 38 40 40 40 40 40 40 40 40 35 35 30 30 30 40
        40 40 39 39 39 40 40 40 40 40 40 40 40 40 40 40 40 40 40 40 40 40 40 40 40
        40 40 40 40 40 40 40 40 40 40 40 40 39 39 39 40 40 40 40 40 40 40 40 40 40
        40 40 40 39 39 39 40 40
        >F2YP0BU02FIING
        32 32 32 25 25 25 25 24 25 30 31 30 27 27 27 28 28 21 19 19 13 13 13 14 19
        19 17 19 16 16 25 28 22 21 17 17 18 25 24 25 25 25
    
    The output file is also SAM:
    
        (SAM header lines omitted)
        F2YP0BU02G7LK5 81  chr21 15557360 255 40M303H        * 0 0 ATTTTATTCTCTTTGAAGCAATTGTGAATGGGAGTTTACT           D>>>>IIIIIIHHG???IIIIIIIIIHHHFFEIH999HII
        F2YP0BU02HXV58 145 chr21 15952091 255 226H40M6S      * 0 0 GCAAATTGTGCTGCTTTAAACATGCGTGTGCAAGTATCTTtttcat     AA===DDDDAAAAD???:::ABBBBBAAA:888ECF;F>>>?8??@
        F2YP0BU02HREML 65  chr21 16386077 255 320H33M5S      * 0 0 CCAAAGTTCTGGGATTACAGGCGTGAGCCATCGcgccc             HH???HHIIIHFHIIIIIIICDDHHIIIIIIHHHHHHH
        F2YP0BU02IOF1F 129 chr21 17567321 255 7S28M409H      * 0 0 taaagagAAGAATTCTCAACCCAGAATTTCATATC                4100<<A>4113:<EFGGGFFFHHHHHHDFFFFED
        F2YP0BU02IKX84 81  chr21 18491628 255 22M1D18M9S341H * 0 0 GTCTCTACCAAAAAATACAAAAATTAGCCGGGCGTGGTGGcatgtctgt  ;;;=7@.55------?2?11112GGB=CCCCDIIIIIIIIIHHHHHHII
        F2YP0BU02GW5VA 145 chr21 20255344 255 286H6S32M      * 0 0 caagaaCAAACACATTCAAAAGCTAGTAGAAGGCAAGA             IIIIIIIHHHIIIIIIICCCCIIIIIIIIIIIIIIIII
        F2YP0BU02JIMJ4 65  chr21 22383051 255 208H19M        * 0 0 CCCTTTATCATTTTTTATT                                555544E?GE113344I22
        F2YP0BU02IXZGF 145 chr21 23094798 255 291H13M1I18M   * 0 0 GCAAGCTCCACTTCCCGGGTTCACGCCATTCT                   IIIIIIIIIIIGG;;;GGHIIIIIGGGIIIII
        F2YP0BU02IODR5 129 chr21 30935325 255 37M154H        * 0 0 GAAATAAAGGGTATTCAATTAGGAAAAGAGGAAGTCA              6...7/--..,30;9<<>@BFFFAAAAHIIIIIH@@@
        F2YP0BU02IMZBL 145 chr21 31603486 255 342H28M1D1M    * 0 0 ATACAAAAATTAGCCGGGCACAGTGGCAG                      BB1552222<<>9==8;;?AA=??A???A
        F2YP0BU02JA9PR 145 chr21 31677159 255 229H23M        * 0 0 CACACCTGTAACCCCAGCACTTT                            IIIIIIIIIIICCCCIIIIIHHH
        F2YP0BU02HKC61 65  chr21 31678718 255 300H40M        * 0 0 CACTGCACTCCAGCCTGGGTGACAAAGCAAGACTCTGTCT           AA@BD:::==AAA@A?8888:<90004<>>?><<<<4442
        F2YP0BU02HKC61 65  chr21 31678718 255 300H40M        * 0 0 CACTGCACTCCAGCCTGGGTGACAAAGCAAGACTCTGTCT           AA@BD:::==AAA@A?8888:<90004<>>?><<<<4442
        F2YP0BU02HVA88 16  chr21 31703558 255 1M1D35M8S      * 0 0 TGGGATTACAGGCGTGAGCTACCACACCCAGCCAGAgttcaaat       >8888DFFHHGFHHHH@@?@?DDC96666HIIIFFFFFFFFFFF
        F2YP0BU02JDCF1 129 chr21 31816600 255 38M103H        * 0 0 AGGAGAATCGCTTGAACCCAGGAGGCAGAGGTTGCGGT             IIIIIIIIIIIHHHIIHHHIIIIIIIIIIIIIIIIIII
        F2YP0BU02GZ1GO 65  chr21 33360122 255 76H6S38M       * 0 0 cctagaCTTCACACACACACACACACACACACACACACACACAC       BBBBD?:688CFFFFFFFFFFFFFFFFFFFFFFFFFFDDBBB51
        F2YP0BU02FX387 145 chr22 14786201 255 201H26M        * 0 0 TGGATGAAGCTGGAAACCATCATTCT                         IIHHHHHHHHHHHHHFFFFFFFFFFF
        F2YP0BU02IF2NE 65  chr22 16960842 255 209H40M10S     * 0 0 TGGCATGCACCTGTAGTCTCAGCTACTTGGGAGGCTGAGGtgggaggatc BAAADDDDFDDDDDDBBA889<A?4444000@<>AA?9444;;8>77<7-
        F2YP0BU02F4TVA 0   chr22 19200522 255 49M            * 0 0 CCTGGGAGGCGGAGGTTGCAGTGAGCCGAGATCACGCCATTGCACTCCA  FFF???FFFFFIIIIIIIIIIIIIIIIIIIIIIIHHIIFHFFFGDDB=5
        F2YP0BU02HKC61 81  chr22 29516998 255 8S32M300H      * 0 0 agacagagTCTTGCTTTGTCACCCAGGCTGGAGTGCAGTG           2444<<<<>?>><40009<:8888?A@AAA==:::DB@AA
        F2YP0BU02FS4EM 65  chr22 30159364 255 339H29M        * 0 0 CTCCTGCCTCAGCCTCCCGAGTAGTTGGG                      IIIIHHEIIIIHHHH??=DDHIIIIIDDD
        F2YP0BU02G197P 129 chr22 32044496 255 40M10S258H     * 0 0 TTGTTGGACATTTGGGTTGGTTCCAAGTCTTTGCTATTGTgaataatgcc IIIIIIIIIIHHHHHHIIIIIIIIIIIII;;;IIIIIIIIIIIIIIIIII
        F2YP0BU02FIING 16  chr22 45959944 255 3M1I11M1I26M   * 0 0 AGCTATGGTACTGGCTATGAAAGCAGACACATAGACCAATGG         :::9:32267=:114244/...446==<<<?@?:9::::AAA
        F2YP0BU02GUB9L 145 chr22 49198404 255 176H16M1I20M   * 0 0 CACCACGCTCGGCTAATTTTTGTATTTTTAGTAGAGA              IIIIIIIIIHAAC;<</////@4F5778;IIIIIIII
    
    """
    left_suffix       = "_L"
    right_suffix      = "_R"
    # Read the mapping
    mate_to_read_dict = {}
    i = 0
    for i, line in enumerate( file( tmp_mates_mapping_file_name, 'rb' ) ):
        line = line.strip()
        if not line.startswith( "#" ):
            fields = line.split()
            if len( fields ) != 4:
                skip_line( "num_fields", i+1, line )
                continue
            mate_name, read_name, s_offset, e_offset = fields
            if mate_name in mate_to_read_dict:
                skip_line( 'two_mate_names', i+1, mate_name )
                continue
            mate_to_read_dict[ mate_name ] = ( read_name, int( s_offset ), int( e_offset ) )
    # Read sequence data
    read_to_nucs_dict = {}
    seqs = 0
    fasta_reader = FastaReader( file( input2, 'rb' ) )
    while True:
        seq = fasta_reader.next()
        if not seq:
            break
        seqs += 1
        seq_text_upper = seq.text.upper()
        if seq.name in read_to_nucs_dict:
            if seq_text_upper != read_to_nucs_dict[ seq.name ]:
                skip_line( 'inconsistent_reads', seqs, seq.name )
                continue
        read_to_nucs_dict[ seq.name ] = seq_text_upper
    # Read quality data
    def quality_sequences( f ):
        seq_name  = None
        seq_quals = None
        line_number = 0
        for line in f:
            line_number += 1
            line = line.strip()
            if line.startswith( ">" ):
                if seq_name != None:
                    yield ( seq_name, seq_quals, seq_line )
                seq_name  = sequence_name( line )
                seq_line  = line_number
                seq_quals = []
            elif seq_name is None:
                skip_line( 'no_header', line_number, line )
                continue
            else:
                seq_quals += [ int( q ) for q in line.split() ]
        if seq_name is not None:
            yield ( seq_name, seq_quals, seq_line )
    def sequence_name( s ):
        s = s[ 1: ].strip()
        if not s:
            return ""
        else:
            return s.split()[ 0 ]
    read_to_quals_dict = {}
    # TODO: should we use Dan's fastaNamedReader here?
    for seq_name, quals, line_number in quality_sequences( file( input4 ) ):
        quals = samify_phred_scores( quals )
        if seq_name in read_to_quals_dict:
            if quals != read_to_quals_dict[ seq_name ]:
                skip_line( 'inconsistent_reads', line_number, seq_name )
            continue
        if len( quals ) != len( read_to_nucs_dict[ seq_name ] ):
            skip_line( 'inconsistent_read_lengths', line_number, seq_name )
            continue
        read_to_quals_dict[ seq_name ] = quals
    # process the SAM file
    tmp_align_file_names = ' '.join( tmp_align_file_name_list )
    combined_chrom_file_name = get_tmp_file_name( suffix='combined_chrom' )
    command = 'cat %s | grep -v "^@" | sort -k 1 > %s' % ( tmp_align_file_names, combined_chrom_file_name )
    run_command( command )
    fout = file( output, 'w+b' )
    has_non_header = False
    i = 0
    for i, line in enumerate( file( combined_chrom_file_name, 'rb' ) ):
        line = line.strip()
        if line.startswith( "@" ):
            if has_non_header:
                skip_line( 'sam_headers', i+1, line )
                continue
            fout.write( "%s\n" % line )
            continue
        has_non_header = True
        fields = line.split()
        num_fields = len( fields )
        if num_fields < SAM_MIN_COLUMNS:
            skip_line( 'sam_min_columns', i+1, line )
            continue
        # Set flags for mates
        try:
            flag = int( fields[ SAM_FLAG_COLUMN ] )
        except ValueError:
            skip_line( 'sam_flag', i+1, line )
            continue
        if not( flag & ( BAM_FPAIRED + BAM_FREAD1 + BAM_FREAD2 ) == 0 ):
            skip_line( 'reads_paired', i+1, line )
            continue
        mate_name = fields[ SAM_QNAME_COLUMN ]
        unmap_it = False
        half = None
        if mate_name.endswith( left_suffix ):
            flag += BAM_FPAIRED + BAM_FREAD2
            fields[ SAM_FLAG_COLUMN ] = "%d" % flag
            unmap_it = True
            half = "L"
        elif mate_name.endswith( right_suffix ):
            flag += BAM_FPAIRED + BAM_FREAD1
            fields[ SAM_FLAG_COLUMN ] = "%d" % flag
            unmap_it = True
            half = "R"
        on_plus_strand = ( flag & BAM_FREVERSE == 0 )
        # Convert position from mate to read by adding clipping to cigar
        if not unmap_it:
            read_name = mate_name
        else:
            try:
                read_name, s_offset, e_offset = mate_to_read_dict[ mate_name ]
            except KeyError:
                skip_line( 'missing_mate', i+1, mate_name )
                continue
            cigar = fields[ SAM_CIGAR_COLUMN ]
            cigar_prefix = None
            cigar_suffix = None
            if half == "L": 
                if on_plus_strand:
                    if s_offset > 0:
                        cigar_prefix = ( s_offset, "S" )
                    if e_offset > 0:
                        cigar_suffix = ( e_offset, "H" )
                else:
                    if e_offset > 0:
                        cigar_prefix = ( e_offset, "H" )
                    if s_offset > 0:
                        cigar_suffix = ( s_offset, "S" )
            elif half == "R": 
                if on_plus_strand:
                    if s_offset > 0:
                        cigar_prefix = ( s_offset, "H" )
                    if e_offset > 0:
                        cigar_suffix = ( e_offset, "S" )
                else:
                    if e_offset > 0:
                        cigar_prefix = ( e_offset, "S" )
                    if s_offset > 0:
                        cigar_suffix = ( s_offset, "H" )
            else:               
                if on_plus_strand:
                    if s_offset > 0:
                        cigar_prefix = ( s_offset, "S" )
                    if e_offset > 0:
                        cigar_suffix = ( e_offset, "S" )
                else:
                    if e_offset > 0:
                        cigar_prefix = ( e_offset, "S" )
                    if s_offset > 0:
                        cigar_suffix = ( s_offset, "S" )
            if cigar_prefix != None:
                count, op = cigar_prefix
                cigar = prefix_cigar( "%d%s" % ( count, op ), cigar )
                if op == "S":
                    refPos = int( fields[ SAM_POS_COLUMN ] ) - count
                    fields[ SAM_POS_COLUMN ] = "%d" % refPos
            if cigar_suffix != None:
                count, op = cigar_suffix
                cigar = suffix_cigar( cigar,"%d%s" % ( count, op) )
            fields[ SAM_QNAME_COLUMN ] = read_name
            fields[ SAM_CIGAR_COLUMN ] = cigar
        # Fetch sequence and quality values, and flip/clip them
        if read_name not in read_to_nucs_dict:
            skip_line( 'missing_seq', i+1, read_name )
            continue
        nucs = read_to_nucs_dict[ read_name ]
        if not on_plus_strand:
            nucs = reverse_complement( nucs )
        quals = None
        if read_to_quals_dict != None:
            if read_name not in read_to_quals_dict:
                skip_line( 'missing_quals', i+1, read_name )
                continue
            quals = read_to_quals_dict[ read_name ]
            if not on_plus_strand:
                quals = reverse_string( quals )
        cigar = split_cigar( fields[ SAM_CIGAR_COLUMN ] )
        nucs, quals = clip_for_cigar( cigar, nucs, quals )
        fields[ SAM_SEQ_COLUMN ] = nucs
        if quals != None:
            fields[ SAM_QUAL_COLUMN ] = quals
        # Output the line
        fout.write( "%s\n" % "\t".join( fields ) )
    fout.close()

def prefix_cigar( prefix, cigar ):
    ix = 0
    while cigar[ ix ].isdigit():
        ix += 1
    if cigar[ ix ] != prefix[ -1 ]:
        return prefix + cigar
    count = int( prefix[ :-1 ] ) + int( cigar[ :ix ] )
    return "%d%s%s" % ( count, prefix[ -1 ], cigar[ ix+1: ] )

def suffix_cigar( cigar, suffix ):
    if cigar[ -1 ] != suffix[ -1 ]:
        return cigar + suffix
    ix = len( cigar ) - 2
    while cigar[ix].isdigit():
        ix -= 1
    ix += 1
    count = int( cigar[ ix:-1 ] ) + int( suffix[ :-1 ] )
    return "%s%d%s" % ( cigar[ :ix ], count, suffix[ -1 ] )

def split_cigar( text ):
    fields = []
    field  = []
    for ch in text:
        if ch not in "MIDHS":
            field += ch
            continue
        if field == []:
            raise ValueError
        fields += [ ( int( "".join( field ) ), ch ) ]
        field = []
    if field != []:
        raise ValueError
    return fields

def clip_for_cigar( cigar, nucs, quals ):
    # Hard clip prefix
    count, op = cigar[0]
    if op == "H":
        nucs = nucs[ count: ]
        if quals != None:
            quals = quals[ count: ]
        count, op = cigar[ 1 ]
    # Soft clip prefix
    if op == "S":
        nucs = nucs[ :count ].lower() + nucs[ count: ]
    # Hard clip suffix
    count,op = cigar[ -1 ]
    if op == "H":
        nucs = nucs[ :-count ]
        if quals != None:
            quals = quals[ :-count ]
        count, op = cigar[ -2 ]
    # Soft clip suffix
    if op == "S":
        nucs = nucs[ :-count ] + nucs[ -count: ].lower()
    return nucs, quals

def samify_phred_scores( quals ):
    """
    Convert a decimal list of phred base-quality scores to a sam quality string.
    Note that if a quality is outside the dynamic range of sam's ability to
    represent it, we clip the value to the max allowed.  SAM quality scores
    range from chr(33) to chr(126).
    """
    if min( quals ) >= 0 and max( quals ) <= 126-33:
        return "".join( [ chr( 33 + q ) for q in quals ] )
    else:
        return "".join( [ chr( max( 33, min( 126, 33+q ) ) ) for q in quals ] )

def reverse_complement( nucs ):
    complementMap = maketrans( "ACGTacgt", "TGCAtgca" )
    return nucs[ ::-1 ].translate( complementMap )

def reverse_string( s ):
    return s[ ::-1 ]

def __main__():
    # Parse command line
    # input1: a reference genome ( 2bit or fasta )
    # input2: a collection of 454 paired end reads ( a fasta file )
    # input3: a linker sequence ( a very small fasta file )
    # input4: a base quality score 454 file ( qual454 )
    parser = optparse.OptionParser()
    parser.add_option( '', '--ref_name', dest='ref_name', help='The reference name to change all output matches to' )
    parser.add_option( '', '--ref_source', dest='ref_source', help='The reference is cached or from the history' )
    parser.add_option( '', '--ref_sequences', dest='ref_sequences', help='Number of sequences in the reference dataset' )
    parser.add_option( '', '--source_select', dest='source_select', help='Use pre-set or cached reference file' )
    parser.add_option( '', '--input1', dest='input1', help='The name of the reference file if using history or reference base name if using cached' )
    parser.add_option( '', '--input2', dest='input2', help='The 454 reads file to align' )
    parser.add_option( '', '--input3', dest='input3', help='The sequencing linker file' )
    parser.add_option( '', '--input4', dest='input4', help='The base quality score 454 file' )
    parser.add_option( '', '--output', dest='output', help='The output file' )
    parser.add_option( '', '--lastz_seqs_file_dir', dest='lastz_seqs_file_dir', help='Directory of local lastz_seqs.loc file' )
    ( options, args ) = parser.parse_args()

    # output version # of tool
    try:
        tmp = tempfile.NamedTemporaryFile().name
        tmp_stdout = open( tmp, 'wb' )
        proc = subprocess.Popen( args='lastz -v', shell=True, stdout=tmp_stdout )
        tmp_stdout.close()
        returncode = proc.wait()
        stdout = None
        for line in open( tmp_stdout.name, 'rb' ):
            if line.lower().find( 'version' ) >= 0:
                stdout = line.strip()
                break
        if stdout:
            sys.stdout.write( '%s\n' % stdout )
        else:
            raise Exception
    except:
        sys.stdout.write( 'Could not determine Lastz version\n' )

    if options.ref_name:
        ref_name = '[nickname=%s]' % options.ref_name
    else:
        ref_name = ''
    if options.ref_source == 'history':
        # Reference is a fasta dataset from the history
        try:
            # Ensure there is at least 1 sequence in the dataset ( this may not be necessary ).
            error_msg = "The reference dataset is missing metadata, click the pencil icon in the history item and 'auto-detect' the metadata attributes."
            ref_sequences = int( options.ref_sequences )
            if ref_sequences < 1:
                stop_err( error_msg )
        except:
            stop_err( error_msg )
    else:
        ref_sequences = 0
    tmp_w12_name = get_tmp_file_name( suffix='vs_linker.W12' )
    tmp_T1_name = get_tmp_file_name( suffix='vs_linker.T1' )
    # Run lastz twice ( with different options ) on the linker sequence and paired end reads,
    # looking for the linker ( each run finds some the other doesn't )
    command = 'lastz %s %s W=12 --notrans --exact=18 --match=1,3 O=1 E=3 Y=10 L=18 --ambiguousn --coverage=85 --format=general-:name2,zstart2+,length2,size2 > %s' % \
        ( options.input3, options.input2, tmp_w12_name )
    run_command( command )
    command = 'lastz %s %s T=1 --match=1,2 O=1 E=2 X=15 K=10 Y=15 L=18 --ambiguousn --coverage=85 --format=general-:name2,zstart2+,length2,size2 > %s' % \
        ( options.input3, options.input2, tmp_T1_name )
    run_command( command )
    # Combine the alignment output from the two lastz runs
    tmp_combined_linker_file_name = get_tmp_file_name( suffix='vs_linker' )
    command = 'cat %s %s | sort -u > %s' % ( tmp_w12_name, tmp_T1_name, tmp_combined_linker_file_name )
    run_command( command )
    # Use the alignment info to split reads into left and right mates
    tmp_mates_mapping_file_name, tmp_mates_file_name, tmp_mates_short_file_name, tmp_mates_long_file_name = split_paired_reads( options.input2, tmp_combined_linker_file_name )
    # Align mates to the reference - tmp_align_file_names is a list of file names created by align_mates()
    tmp_align_file_name_list = align_mates( options.input1, options.ref_source, ref_name, ref_sequences, tmp_mates_short_file_name, tmp_mates_long_file_name )
    # Combine and convert mate coordinates back to read coordinates
    paired_mate_unmapper( options.input2, options.input4, tmp_mates_mapping_file_name, tmp_align_file_name_list, options.output )
    # Delete all temporary files
    for file_name in tmp_file_names:
        os.remove( file_name )
    # Handle any invalid lines in the input data
    if total_skipped_lines:
        msgs = dict( bad_interval="Bad interval in line",
                     inconsistent_read_lengths="Inconsistent read/quality lengths for seq #",
                     inconsistent_reads="Inconsistent reads for seq #",
                     inconsistent_sizes="Inconsistent sizes for seq #",
                     missing_mate="Mapping file does not include mate on line",
                     missing_quals="Missing quality values for name on line",
                     missing_seq="Missing sequence for name on line",
                     multiple_seqs="Multiple names for seq #",
                     no_header="First quality sequence has no header",
                     num_fields="Must have 4 fields in line",
                     reads_paired="SAM flag indicates reads already paired on line",
                     sam_flag="Bad SAM flag on line",
                     sam_headers="SAM headers on line",
                     sam_min_columns="Need 11 columns on line",
                     two_mate_names="Mate name already seen, line",
                     wrong_seq_len="Size differs from length of seq #" )
        print "Skipped %d invalid lines: "
        msg = ""
        for k, v in skipped_lines.items():
            if v[0]:
                # v[0] is the number of times the error occurred
                # v[1] is the position of the line or sequence in the file
                # v[2] is the name of the sequence or the text of the line
                msg += "(%d)%s %d:%s. " % ( v[0], msgs[k], v[1], v[2] )
        print msg

if __name__=="__main__": __main__()
