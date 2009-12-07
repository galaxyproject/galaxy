#! /usr/bin/python

"""
Runs Lastz
Written for Lastz v. 1.01.88.

usage: lastz_wrapper.py [options]
    --ref_name: The reference name to change all output matches to
    --ref_source: Whether the reference is cached or from the history
    --source_select: Whether to used pre-set or cached reference file
    --input1: The name of the reference file if using history or reference base name if using cached
    --input2: The reads file to align 
    --ref_sequences: The number of sequences in the reference file if using one from history 
    --pre_set_options: Which of the pre set options to use, if using pre-sets
    --strand: Which strand of the read to search, if specifying all parameters
    --seed: Seeding settings, if specifying all parameters
    --gfextend: Whether to perform gap-free extension of seed hits to HSPs (high scoring segment pairs), if specifying all parameters
    --chain: Whether to perform chaining of HSPs, if specifying all parameters
    --transition: Number of transitions to allow in each seed hit, if specifying all parameters
    --O: Gap opening penalty, if specifying all parameters
    --E: Gap extension penalty, if specifying all parameters
    --X: X-drop threshold, if specifying all parameters
    --Y: Y-drop threshold, if specifying all parameters
    --K: Threshold for HSPs, if specifying all parameters
    --L: Threshold for gapped alignments, if specifying all parameters
    --entropy: Whether to involve entropy when filtering HSPs, if specifying all parameters
    --identity_min: Minimum identity (don't report matches under this identity)
    --identity_max: Maximum identity (don't report matches above this identity)
    --coverage: The minimum coverage value (don't report matches covering less than this) 
    --out_format: The format of the output file (sam, diffs, or tabular (general))
    --output: The name of the output file
    --num_threads: The number of threads to run
    --lastzSeqsFileDir: Directory of local lastz_seqs.loc file
"""
import optparse, os, subprocess, shutil, sys, tempfile, threading
from Queue import Queue

from galaxy import eggs
import pkg_resources
pkg_resources.require( 'bx-python' )
from bx.seq.twobit import *
from bx.seq.fasta import FastaReader

def stop_err( msg ):
    sys.stderr.write( "%s" % msg )
    sys.exit()

class LastzJobRunner( object ):
    """
    Lastz job runner backed by a pool of "num_threads" worker threads. FIFO scheduling
    """
    def __init__( self, num_threads, commands ):
        """Start the job runner with "num_threads" worker threads"""
        # start workers
        self.queue = Queue()
        for command in commands:
            self.queue.put( command )
        self.threads = []
        for i in range( num_threads ):
            worker = threading.Thread( target=self.run_next )
            worker.start()
            self.threads.append( worker )
        for worker in self.threads:
            worker.join()
    def run_next( self ):
        """Run the next command, waiting until one is available if necessary"""
        while not self.queue.empty():
            command = self.queue.get()
            self.run_job( command )
    def run_job( self, command ):
        try:
            proc = subprocess.Popen( args=command, shell=True )
            proc.wait()
        except Exception, e:
            stop_err( "Error executing command (%s) - %s" % ( str( command ), str( e ) ) )

def __main__():
    #Parse Command Line
    parser = optparse.OptionParser()
    parser.add_option( '', '--ref_name', dest='ref_name', help='The reference name to change all output matches to' )
    parser.add_option( '', '--ref_source', dest='ref_source', help='Whether the reference is cached or from the history' )
    parser.add_option( '', '--ref_sequences', dest='ref_sequences', help='Number of sequences in the reference dataset' )
    parser.add_option( '', '--source_select', dest='source_select', help='Whether to used pre-set or cached reference file' )
    parser.add_option( '', '--input1', dest='input1', help='The name of the reference file if using history or reference base name if using cached' )
    parser.add_option( '', '--input2', dest='input2', help='The reads file to align' )
    parser.add_option( '', '--pre_set_options', dest='pre_set_options', help='Which of the pre set options to use, if using pre-sets' )
    parser.add_option( '', '--strand', dest='strand', help='Which strand of the read to search, if specifying all parameters' )
    parser.add_option( '', '--seed', dest='seed', help='Seeding settings, if specifying all parameters' )
    parser.add_option( '', '--transition', dest='transition', help='Number of transitions to allow in each seed hit, if specifying all parameters' )
    parser.add_option( '', '--gfextend', dest='gfextend', help='Whether to perform gap-free extension of seed hits to HSPs (high scoring segment pairs), if specifying all parameters' )
    parser.add_option( '', '--chain', dest='chain', help='Whether to perform chaining of HSPs, if specifying all parameters' )
    parser.add_option( '', '--O', dest='O', help='Gap opening penalty, if specifying all parameters' )
    parser.add_option( '', '--E', dest='E', help='Gap extension penalty, if specifying all parameters' )
    parser.add_option( '', '--X', dest='X', help='X-drop threshold, if specifying all parameters' )
    parser.add_option( '', '--Y', dest='Y', help='Y-drop threshold, if specifying all parameters' )
    parser.add_option( '', '--K', dest='K', help='Threshold for HSPs, if specifying all parameters' )
    parser.add_option( '', '--L', dest='L', help='Threshold for gapped alignments, if specifying all parameters' )
    parser.add_option( '', '--entropy', dest='entropy', help='Whether to involve entropy when filtering HSPs, if specifying all parameters' )
    parser.add_option( '', '--identity_min', dest='identity_min', help="Minimum identity (don't report matches under this identity)" )
    parser.add_option( '', '--identity_max', dest='identity_max', help="Maximum identity (don't report matches above this identity)" )
    parser.add_option( '', '--coverage', dest='coverage', help="The minimum coverage value (don't report matches covering less than this)" )
    parser.add_option( '', '--out_format', dest='format', help='The format of the output file (sam, diffs, or tabular (general))' )
    parser.add_option( '', '--output', dest='output', help='The output file' )
    parser.add_option( '', '--num_threads', dest='num_threads', help='The number of threads to run' )
    parser.add_option( '', '--lastzSeqsFileDir', dest='lastzSeqsFileDir', help='Directory of local lastz_seqs.loc file' )
    ( options, args ) = parser.parse_args()

    # If the reference sequences are from the history, temporary input files will be created
    # ( 1 for each sequence ), and we'll keep track of them for later removal from disk ( by closing them )
    tmp_in_file_names = []
    # Each thread will create a temporary file to which it writes the output from lastz
    tmp_out_file_names = []
    # Execution of lastz based on job splitting
    commands = []
    if options.ref_name != 'None':
        ref_name = '[nickname=%s]' % options.ref_name
    else:
        ref_name = ''
    # Prepare for commonly-used preset options
    if options.source_select == 'pre_set':
        set_options = '--%s' % options.pre_set_options
    # Prepare for user-specified options
    else:
        set_options = '--%s --%s --gapped --strand=%s --seed=%s --%s O=%s E=%s X=%s Y=%s K=%s L=%s --%s' % \
                    ( options.gfextend, options.chain, options.strand, options.seed, 
                      options.transition, options.O, options.E, options.X, 
                      options.Y, options.K, options.L, options.entropy )
    # Specify input2 and add [fullnames] modifier if output format is diffs
    if options.format == 'diffs':
        input2 = '%s[fullnames]' % options.input2
    else:
        input2 = options.input2
    if options.format == 'tabular':
        # Change output format to general if it's tabular and add field names for tabular output
        format = 'general-'
        tabular_fields = ':score,name1,strand1,size1,start1,zstart1,end1,length1,text1,name2,strand2,size2,start2,zstart2,end2,start2+,zstart2+,end2+,length2,text2,diff,cigar,identity,coverage,gaprate,diagonal,shingle'
    elif options.format == 'sam':
        # We currently ALWAYS suppress SAM headers.
        format = 'sam-'
        tabular_fields = ''
    else:
        format = options.format
        tabular_fields = ''
    if options.ref_source == 'history':
        # Reference is a fasta dataset from the history, so split job across number of sequences in the dataset
        try:
            # Ensure there is at least 1 sequence in the dataset ( this may not be necessary ).
            error_msg = "The reference dataset is missing metadata, click the pencil icon in the history item and 'auto-detect' the metadata attributes."
            ref_sequences = int( options.ref_sequences )
            if ref_sequences < 1:
                stop_err( error_msg )
        except:
            stop_err( error_msg )
        seqs = 0
        fasta_reader = FastaReader( open( options.input1 ) )
        while True:
            # Read the next sequence from the reference dataset
            seq = fasta_reader.next()
            if not seq:
                break
            seqs += 1
            # Create a temporary file to contain the current sequence as input to lastz
            tmp_in = tempfile.NamedTemporaryFile( prefix=seq.name, suffix='.fasta' )
            tmp_in_name = tmp_in.name
            tmp_in.close()
            tmp_in = file(tmp_in_name,'w+b')
            # Keep track of our list of temporary input files so we can remove them later by closing them
            tmp_in_file_names.append( tmp_in_name )
            # Write the current sequence to the temporary input file
            tmp_in.write( '>%s\n%s\n' % ( seq.name, seq.text ) )
            tmp_in.close()
            # Create a 2nd temporary file to contain the output from lastz execution on the current sequence
            tmp_out = tempfile.NamedTemporaryFile( prefix='%s_out' % seq.name )
            tmp_out_name = tmp_out.name
            tmp_out.close()
            # Keep track of our list of temporary output files so we can merge them into our output dataset
            tmp_out_file_names.append( tmp_out_name )
            # Generate the command line for calling lastz on the current sequence
            command = 'lastz %s%s %s %s --ambiguousn --nolaj --identity=%s..%s --coverage=%s --format=%s%s > %s' % \
                ( tmp_in_name, ref_name, input2, set_options, options.identity_min, 
                  options.identity_max, options.coverage, format, tabular_fields, tmp_out_name )
            # Append the command line to our list of commands for sending to the LastzJobRunner queue
            commands.append( command )
        # Make sure the value of sequences in the metadata is the
        # same as the number of sequences read from the dataset ( this may not be necessary ).
        if ref_sequences != seqs:
            stop_error( "The value of metadata.sequences (%d) differs from the number of sequences read from the reference ( %d)." % ( ref_sequences, seqs ) )
    else:
        # Reference is a locally cached 2bit file, split job across number of chroms in 2bit file
        tbf = TwoBitFile( open( options.input1, 'r' ) )
        for chrom in tbf.keys():
            # Create a temporary file to contain the output from lastz execution on the current chrom
            tmp_out = tempfile.NamedTemporaryFile( prefix='%s_out' % chrom )
            tmp_out_name = tmp_out.name
            tmp_out.close()
            # Keep track of our list of temporary output files so we can merge them into our output dataset
            tmp_out_file_names.append( tmp_out_name )
            command = 'lastz %s/%s%s %s %s --ambiguousn --nolaj --identity=%s..%s --coverage=%s --format=%s%s >> %s' % \
                ( options.input1, chrom, ref_name, input2, set_options, options.identity_min, 
                  options.identity_max, options.coverage, format, tabular_fields, tmp_out_name )
            commands.append( command )
    job_runner = LastzJobRunner( int( options.num_threads ), commands )
    # Merge all of the output from lastz ( currently in temporary files ) into our output dataset
    command = 'cat %s >> %s' % ( ' '.join( tmp_out_file_names ), options.output )
    proc = subprocess.Popen( args=command, shell=True )
    proc.wait()
    # Remove all temporary files from disk by closing them
    for name in tmp_in_file_names:
        try:
            os.remove( name )
        except:
            pass
    for name in tmp_out_file_names:
        try:
            os.remove( name )
        except:
            pass

if __name__=="__main__": __main__()
