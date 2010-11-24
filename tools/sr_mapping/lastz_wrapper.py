#!/usr/bin/env python

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
    --unmask: Whether to convert lowercase bases to uppercase
    --out_format: The format of the output file (sam, diffs, or tabular (general))
    --output: The name of the output file
    --lastzSeqsFileDir: Directory of local lastz_seqs.loc file
"""
import optparse, os, subprocess, shutil, sys, tempfile, threading, time
from Queue import Queue

from galaxy import eggs
import pkg_resources
pkg_resources.require( 'bx-python' )
from bx.seq.twobit import *
from bx.seq.fasta import FastaReader
from galaxy.util.bunch import Bunch

STOP_SIGNAL = object()
WORKERS = 4
SLOTS = 128

def stop_err( msg ):
    sys.stderr.write( "%s" % msg )
    sys.exit()

def stop_queues( lastz, combine_data ):
    # This method should only be called if an error has been encountered.
    # Send STOP_SIGNAL to all worker threads
    for t in lastz.threads:
        lastz.put( STOP_SIGNAL, True )
    combine_data.put( STOP_SIGNAL, True )

class BaseQueue( object ):
    def __init__( self, num_threads, slots=-1 ):
        # Initialize the queue and worker threads
        self.queue = Queue( slots )
        self.threads = []
        for i in range( num_threads ):
            worker = threading.Thread( target=self.run_next )
            worker.start()
            self.threads.append( worker )
    def run_next( self ):
        # Run the next job, waiting until one is available if necessary
        while True:
            job = self.queue.get()
            if job is STOP_SIGNAL:
                return self.shutdown()
            self.run_job( job )
            time.sleep( 1 )
    def run_job( self, job ):
        stop_err( 'Not Implemented' )
    def put( self, job, block=False ):
        # Add a job to the queue
        self.queue.put( job, block )
    def shutdown( self ):
        return

class LastzJobQueue( BaseQueue ):
    """
    A queue that runs commands in parallel.  Blocking is done so the queue will
    not consume much memory.
    """
    def run_job( self, job ):
        # Execute the job's command
        proc = subprocess.Popen( args=job.command, shell=True, stderr=subprocess.PIPE, )
        proc.wait()
        stderr = proc.stderr.read()
        proc.wait()
        if stderr:
            stop_queues( self, job.combine_data_queue )
            stop_err( stderr )
        job.combine_data_queue.put( job )

class CombineDataQueue( BaseQueue ):
    """
    A queue that concatenates files in serial.  Blocking is not done since this
    queue is not expected to grow larger than the command queue.
    """
    def __init__( self, output_filename, num_threads=1 ):
        BaseQueue.__init__( self, num_threads )
        self.CHUNK_SIZE = 2**20 # 1Mb
        self.output_file = open( output_filename, 'wb' )
    def run_job( self, job ):
        in_file = open( job.output, 'rb' )
        while True:
            chunk = in_file.read( self.CHUNK_SIZE )
            if not chunk:
                in_file.close()
                break
            self.output_file.write( chunk )
        for file_name in job.cleanup:
            os.remove( file_name )
    def shutdown( self ):
        self.output_file.close()
        return

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
    parser.add_option( '', '--unmask', dest='unmask', help='Whether to convert lowercase bases to uppercase' )
    parser.add_option( '', '--out_format', dest='format', help='The format of the output file (sam, diffs, or tabular (general))' )
    parser.add_option( '', '--output', dest='output', help='The output file' )
    parser.add_option( '', '--lastzSeqsFileDir', dest='lastzSeqsFileDir', help='Directory of local lastz_seqs.loc file' )
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

    if options.unmask == 'yes':
        unmask = '[unmask]'
    else:
        unmask = ''
    if options.ref_name:
        ref_name = '[nickname=%s]' % options.ref_name
    else:
        ref_name = ''
    # Prepare for commonly-used preset options
    if options.source_select == 'pre_set':
        set_options = '--%s' % options.pre_set_options
    # Prepare for user-specified options
    else:
        set_options = '--%s --%s --gapped --strand=%s --seed=%s --%s O=%s E=%s X=%s Y=%s K=%s L=%s --%s' % \
                    ( options.gfextend, options.chain, options.strand, options.seed, options.transition,
                      options.O, options.E, options.X, options.Y, options.K, options.L, options.entropy )
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

    # Set up our queues
    lastz_job_queue = LastzJobQueue( WORKERS, slots=SLOTS )
    combine_data_queue = CombineDataQueue( options.output )

    if options.ref_source == 'history':
        # Reference is a fasta dataset from the history, so split job across
        # the number of sequences in the dataset ( this could be a HUGE number )
        try:
            # Ensure there is at least 1 sequence in the dataset ( this may not be necessary ).
            error_msg = "The reference dataset is missing metadata, click the pencil icon in the history item and 'auto-detect' the metadata attributes."
            ref_sequences = int( options.ref_sequences )
            if ref_sequences < 1:
                stop_queues( lastz_job_queue, combine_data_queue )
                stop_err( error_msg )
        except:
            stop_queues( lastz_job_queue, combine_data_queue )
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
            tmp_in_fd, tmp_in_name = tempfile.mkstemp( suffix='.in' )
            tmp_in = os.fdopen( tmp_in_fd, 'wb' )
            # Write the current sequence to the temporary input file
            tmp_in.write( '>%s\n%s\n' % ( seq.name, seq.text ) )
            tmp_in.close()
            # Create a 2nd temporary file to contain the output from lastz execution on the current sequence
            tmp_out_fd, tmp_out_name = tempfile.mkstemp( suffix='.out' )
            os.close( tmp_out_fd )
            # Generate the command line for calling lastz on the current sequence
            command = 'lastz %s%s%s %s %s --ambiguousn --nolaj --identity=%s..%s --coverage=%s --format=%s%s > %s' % \
                ( tmp_in_name, unmask, ref_name, input2, set_options, options.identity_min, 
                  options.identity_max, options.coverage, format, tabular_fields, tmp_out_name )
            # Create a job object
            job = Bunch()
            job.command = command
            job.output = tmp_out_name
            job.cleanup = [ tmp_in_name, tmp_out_name ]
            job.combine_data_queue = combine_data_queue
            # Add another job to the lastz_job_queue. Execution 
            # will wait at this point if the queue is full.
            lastz_job_queue.put( job, block=True )
        # Make sure the value of sequences in the metadata is the same as the
        # number of sequences read from the dataset ( this may not be necessary ).
        if ref_sequences != seqs:
            stop_queues( lastz_job_queue, combine_data_queue )
            stop_err( "The value of metadata.sequences (%d) differs from the number of sequences read from the reference (%d)." % ( ref_sequences, seqs ) )
    else:
        # Reference is a locally cached 2bit file, split job across number of chroms in 2bit file
        tbf = TwoBitFile( open( options.input1, 'r' ) )
        for chrom in tbf.keys():
            # Create a temporary file to contain the output from lastz execution on the current chrom
            tmp_out_fd, tmp_out_name = tempfile.mkstemp( suffix='.out' )
            os.close( tmp_out_fd )
            command = 'lastz %s/%s%s%s %s %s --ambiguousn --nolaj --identity=%s..%s --coverage=%s --format=%s%s >> %s' % \
                ( options.input1, chrom, unmask, ref_name, input2, set_options, options.identity_min, 
                  options.identity_max, options.coverage, format, tabular_fields, tmp_out_name )
            # Create a job object
            job = Bunch()
            job.command = command
            job.output = tmp_out_name
            job.cleanup = [ tmp_out_name ]
            job.combine_data_queue = combine_data_queue
            # Add another job to the lastz_job_queue. Execution 
            # will wait at this point if the queue is full.
            lastz_job_queue.put( job, block=True )

    # Stop the lastz_job_queue
    for t in lastz_job_queue.threads:
        lastz_job_queue.put( STOP_SIGNAL, True )
    # Although all jobs are submitted to the queue, we can't shut down the combine_data_queue
    # until we know that all jobs have been submitted to its queue.  We do this by checking
    # whether all of the threads in the lastz_job_queue have terminated.
    while threading.activeCount() > 2:
        time.sleep( 1 )
    # Now it's safe to stop the combine_data_queue
    combine_data_queue.put( STOP_SIGNAL )

if __name__=="__main__": __main__()
