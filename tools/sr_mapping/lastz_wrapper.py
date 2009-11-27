#! /usr/bin/python

"""
    --lastzSeqsFileDir: Directory of local lastz_seqs.loc file
"""
import optparse, os, subprocess, shutil, sys, tempfile, threading
from Queue import Queue

from galaxy import eggs
import pkg_resources
pkg_resources.require( 'bx-python' )
from bx.seq.twobit import *

def stop_err( msg ):
    sys.stderr.write( "%s\n" % msg )
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
    def run_next( self ):
        """Run the next command, waiting until one is available if necessary"""
        while not self.queue.empty():
            command = self.queue.get()
            self.run_job( command )
    def run_job( self, command ):
        try:
            proc = subprocess.Popen( args=command, shell=True )
            sts = os.waitpid( proc.pid, 0 )
        except Exception, e:
            stop_err( "Error executing command (%s) - %s" % ( str( command ), str( e ) ) )

def __main__():
    #Parse Command Line
    parser = optparse.OptionParser()
    parser.add_option( '', '--ref_name', dest='ref_name', help='' )
    parser.add_option( '', '--ref_source', dest='ref_source', help='' )
    parser.add_option( '', '--ref_sequences', dest='ref_sequences', help='Number of sequences in the reference dataset' )
    parser.add_option( '', '--source_select', dest='source_select', help='' )
    parser.add_option( '', '--out_format', dest='out_format', help='' )
    parser.add_option( '', '--input1', dest='input1', help='' )
    parser.add_option( '', '--input2', dest='input2', help='' )
    parser.add_option( '', '--pre_set_options', dest='pre_set_options', help='' )
    parser.add_option( '', '--strand', dest='strand', help='' )
    parser.add_option( '', '--seed', dest='seed', help='' )
    parser.add_option( '', '--transition', dest='transition', help='' )
    parser.add_option( '', '--gfextend', dest='gfextend', help='' )
    parser.add_option( '', '--nogfextend', dest='nogfextend', help='' )
    parser.add_option( '', '--chain', dest='chain', help='' )
    parser.add_option( '', '--nochain', dest='nochain', help='' )
    parser.add_option( '', '--gapped', dest='gapped', help='' )
    parser.add_option( '', '--nogapped', dest='nogapped', help='' )
    parser.add_option( '', '--O', dest='O', help='' )
    parser.add_option( '', '--E', dest='E', help='' )
    parser.add_option( '', '--X', dest='X', help='' )
    parser.add_option( '', '--Y', dest='Y', help='' )
    parser.add_option( '', '--K', dest='K', help='' )
    parser.add_option( '', '--L', dest='L', help='' )
    parser.add_option( '', '--entropy', dest='entropy', help='' )
    parser.add_option( '', '--identity_min', dest='identity_min', help='' )
    parser.add_option( '', '--identity_max', dest='identity_max', help='' )
    parser.add_option( '', '--coverage', dest='coverage', help='' )
    parser.add_option( '', '--format', dest='format', help='' )
    parser.add_option( '', '--output', dest='output', help='The output file' )
    parser.add_option( '', '--num_threads', dest='num_threads', help='' )
    parser.add_option( '', '--lastzSeqsFileDir', dest='lastzSeqsFileDir', help='Directory of local lastz_seqs.loc file' )
    ( options, args ) = parser.parse_args()

    commands = []
    if options.ref_name != 'None':
        ref_name = '%s::' % options.ref_name
    else:
        ref_name = ''
    # Prepare for commonly-used preset options
    if options.source_select == 'pre_set':
        set_options = '--%s' % options.pre_set_options
    # Prepare for user-specified options
    else:
        set_options = '%s %s --%s --%s --%s --%s O=%s E=%s X=%s Y=%s K=%s L=%s %s' % \
                    ( options.gfextend, options.chain, options.gapped, options.strand, 
                      options.seed, options.transition, options.O, options.E, options.X, 
                      options.Y, options.K, options.L, options.entropy )
    # Specify input2 and add [fullnames] modifier if output format is diffs
    if options.format == 'diffs':
        input2 = '%s[fullnames]' % options.input2
    else:
        input2 = options.input2
    if options.format == 'tabular':
        # Change output format to general if it's tabular and add field names for tabular output
        format = 'general'
        tabular_fields = ':score,name1,strand1,size1,start1,zstart1,end1,length1,text1,name2,strand2,size2,start2,zstart2,end2,start2+,zstart2+,end2+,length2,text2,diff,cigar,identity,coverage,gaprate,diagonal,shingle'
    else:
        format = options.format
        tabular_fields = ''
    if options.ref_source == 'history':
        # Reference is a fasta dataset from the history, so split job across number of
        # sequences in the dataset
        try:
            error_msg = "The reference dataset is missing metadata, click the pencil icon in the history item and 'auto-detect' the metadata attributes."
            ref_sequences = int( options.ref_sequences )
            if ref_sequences < 1:
                stop_err( error_msg )
        except:
            stop_err( error_msg )
        for seq in range( ref_sequences ):
            command = 'lastz %s%s %s %s --ambiguousn --nolaj --identity=%s..%s --coverage=%s --format=%s%s >> %s' % \
                ( ref_name, options.input1, input2, set_options, options.identity_min, 
                  options.identity_max, options.coverage, format, tabular_fields, options.output )
            commands.append( command )
    else:
        # Reference is a locally cached 2bit file, split job across number of chroms in 2bit file
        tbf = TwoBitFile( open( options.input1, 'r' ) )
        for chrom in tbf.keys():
            command = 'lastz %s%s/%s %s %s --ambiguousn --nolaj --identity=%s..%s --coverage=%s --format=%s%s >> %s' % \
                ( ref_name, options.input1, chrom, input2, set_options, options.identity_min, 
                  options.identity_max, options.coverage, format, tabular_fields, options.output )
            commands.append( command )
        tbf.close()
    job_runner = LastzJobRunner( int( options.num_threads ), commands )

if __name__=="__main__": __main__()
