#!/usr/bin/env python

import argparse, os, shutil, subprocess, sys, tempfile, fileinput
import fileinput
from glob import glob

def stop_err( msg ):
    sys.stderr.write( "%s\n" % msg )
    sys.exit()

def __main__():
    #Parse Command Line
    parser = argparse.ArgumentParser(description='Wrapper for the bismark bisulfite mapper.')
    parser.add_argument( '-p', '--num-threads', dest='num_threads',
        type=int, default=4, help='Use this many threads to align reads. The default is 4.' )

    parser.add_argument( '--bismark_path', dest='bismark_path', help='Path to the bismark perl scripts' )

    parser.add_argument( '--bowtie2', action='store_true', default=False, help='Running bismark with bowtie2 and not with bowtie.' )

    # input options
    parser.add_argument( '--own-file', dest='own_file', help='' )
    parser.add_argument( '-D', '--indexes-path', dest='index_path', help='Indexes directory; location of .ebwt and .fa files.' )
    parser.add_argument( '-O', '--output', dest='output' )
    parser.add_argument( '--output-report-file', dest='output_report_file' )
    parser.add_argument( '--suppress-header', dest='suppress_header', action="store_true" )

    parser.add_argument( '--mate-paired', dest='mate_paired', action='store_true', help='Reads are mate-paired', default=False)


    parser.add_argument( '-1', '--mate1', dest='mate1',
        help='The forward reads file in Sanger FASTQ or FASTA format.' )
    parser.add_argument( '-2', '--mate2', dest='mate2',
        help='The reverse reads file in Sanger FASTQ or FASTA format.' )

    parser.add_argument( '--output-unmapped-reads', dest='output_unmapped_reads',
        help='Additional output file with unmapped reads (single-end).' )
    parser.add_argument( '--output-unmapped-reads-l', dest='output_unmapped_reads_l',
        help='File name for unmapped reads (left, paired-end).' )
    parser.add_argument( '--output-unmapped-reads-r', dest='output_unmapped_reads_r',
        help='File name for unmapped reads (right, paired-end).' )
   
   
    parser.add_argument( '--output-suppressed-reads', dest='output_suppressed_reads',
        help='Additional output file with suppressed reads (single-end).' )
    parser.add_argument( '--output-suppressed-reads-l', dest='output_suppressed_reads_l',
        help='File name for suppressed reads (left, paired-end).' )
    parser.add_argument( '--output-suppressed-reads-r', dest='output_suppressed_reads_r',
        help='File name for suppressed reads (right, paired-end).' )


    parser.add_argument( '--single-paired', dest='single_paired',
         help='The single-end reads file in Sanger FASTQ or FASTA format.' )

    parser.add_argument( '--fastq', action='store_true', help='Query filetype is in FASTQ format')
    parser.add_argument( '--fasta', action='store_true', help='Query filetype is in FASTA format')
    parser.add_argument( '--phred64-quals', dest='phred64', action="store_true" )


    parser.add_argument( '--skip-reads', dest='skip_reads', type=int )
    parser.add_argument( '--qupto', type=int)


    # paired end options
    parser.add_argument( '-I', '--minins', dest='min_insert' )
    parser.add_argument( '-X', '--maxins', dest='max_insert' )
    parser.add_argument( '--no-mixed', dest='no_mixed', action="store_true" )
    parser.add_argument( '--no-discordant', dest='no_discordant', action="store_true" )

    #parse general options
    # default 20
    parser.add_argument( '--seed-len', dest='seed_len', type=int)
    # default 15
    parser.add_argument( '--seed-extention-attempts', dest='seed_extention_attempts', type=int )
    # default 0
    parser.add_argument( '--seed-mismatches', dest='seed_mismatches', type=int )
    # default 2
    parser.add_argument( '--max-reseed', dest='max_reseed', type=int )
    """
    # default 70
    parser.add_argument( '--maqerr', dest='maqerr', type=int )
    """
    
    """
    The number of megabytes of memory a given thread is given to store path
    descriptors in --best mode. Best-first search must keep track of many paths
    at once to ensure it is always extending the path with the lowest cumulative
    cost. Bowtie tries to minimize the memory impact of the descriptors, but
    they can still grow very large in some cases. If you receive an error message
    saying that chunk memory has been exhausted in --best mode, try adjusting
    this parameter up to dedicate more memory to the descriptors. Default: 512.
    """
    parser.add_argument( '--chunkmbs', type=int, default=512 )

    args = parser.parse_args()
    
    # Create bismark index if necessary.
    index_dir = ""
    if args.own_file:
        """
            Create a temporary index with the offered files from the user.
            Utilizing the script: bismark_genome_preparation
            bismark_genome_preparation --bowtie2 hg19/
        """
        tmp_index_dir = tempfile.mkdtemp()
        index_path = os.path.join( tmp_index_dir, '.'.join( os.path.split( args.own_file )[1].split( '.' )[:-1] ) )
        try:
            """
                Create a hard link pointing to args.own_file named 'index_path'.fa.
            """
            os.symlink( args.own_file, index_path + '.fa' )
        except Exception, e:
            if os.path.exists( tmp_index_dir ):
                shutil.rmtree( tmp_index_dir )
            stop_err( 'Error in linking the reference database.\n' + str( e ) )
        # bismark_genome_preparation needs the complete path to the folder in which the database is stored
        if args.bowtie2:
            cmd_index = 'bismark_genome_preparation --bowtie2 %s ' % ( tmp_index_dir )
        else:
            cmd_index = 'bismark_genome_preparation %s ' % ( tmp_index_dir )
        if args.bismark_path:
            # add the path to the bismark perl scripts, that is needed for galaxy
            cmd_index = '%s/%s' % (args.bismark_path, cmd_index)
        try:
            tmp = tempfile.NamedTemporaryFile( dir=tmp_index_dir ).name
            tmp_stderr = open( tmp, 'wb' )
            proc = subprocess.Popen( args=cmd_index, shell=True, cwd=tmp_index_dir, stdout=open(os.devnull, 'wb'), stderr=tmp_stderr.fileno() )
            returncode = proc.wait()
            tmp_stderr.close()
            # get stderr, allowing for case where it's very large
            tmp_stderr = open( tmp, 'rb' )
            stderr = ''
            buffsize = 1048576
            try:
                while True:
                    stderr += tmp_stderr.read( buffsize )
                    if not stderr or len( stderr ) % buffsize != 0:
                        break
            except OverflowError:
                pass
            tmp_stderr.close()
            if returncode != 0:
                raise Exception, stderr
        except Exception, e:
            if os.path.exists( tmp_index_dir ):
                shutil.rmtree( tmp_index_dir )
            stop_err( 'Error indexing reference sequence\n' + str( e ) )
        index_dir = tmp_index_dir
    else:
        index_dir = args.index_path

    # Build bismark command
    tmp_bismark_dir = tempfile.mkdtemp()
    output_dir = os.path.join( tmp_bismark_dir, 'results')
    cmd = 'bismark %(args)s --temp_dir %(tmp_bismark_dir)s -o %(output_dir)s --quiet %(genome_folder)s %(reads)s'
    if args.bismark_path:
        # add the path to the bismark perl scripts, that is needed for galaxy
        cmd = '%s/%s' % (args.bismark_path, cmd)

    arguments = {
        'genome_folder': index_dir,
        'args': '',
        'tmp_bismark_dir': tmp_bismark_dir,
        'output_dir': output_dir,
        }

    additional_opts = ''
    # Set up the reads
    if args.mate_paired:
        # paired-end reads library
        reads = '-1 %s ' % ( args.mate1 )
        reads += ' -2 %s ' % ( args.mate2 )
        additional_opts += ' -I %s -X %s ' % (args.min_insert, args.max_insert)
    else:
        # single paired reads library
        reads = ' %s ' % ( args.single_paired )


    if not args.bowtie2:
        # use bowtie specific options
        additional_opts += ' --best '
        if args.seed_mismatches:
            # --seedmms
            additional_opts += ' -n %s ' % args.seed_mismatches
        if args.seed_len:
            # --seedlen
            additional_opts += ' -l %s ' % args.seed_len

    # alignment options
    if args.bowtie2:
        additional_opts += ' -p %s --bowtie2 ' % args.num_threads
        if args.seed_mismatches:
            additional_opts += ' -N %s ' % args.seed_mismatches
        if args.seed_len:
            additional_opts += ' -L %s ' % args.seed_len
        if args.seed_extention_attempts:
            additional_opts += ' -D %s ' % args.seed_extention_attempts
        if args.max_reseed:
            additional_opts += ' -R %s ' % args.max_reseed
        if args.no_discordant:
            additional_opts += ' --no-discordant '
        if args.no_mixed:
            additional_opts += ' --no-mixed '
    """
    if args.maqerr:
        additional_opts += ' --maqerr %s ' % args.maqerr
    """
    if args.skip_reads:
        additional_opts += ' --skip %s ' % args.skip_reads
    if args.qupto:
        additional_opts += ' --qupto %s ' % args.qupto
    if args.phred64:
        additional_opts += ' --phred64-quals '
    if args.suppress_header:
        additional_opts += ' --sam-no-hd  '
    if args.output_unmapped_reads or ( args.output_unmapped_reads_l and args.output_unmapped_reads_r):
        additional_opts += ' --un '
    if args.output_suppressed_reads or ( args.output_suppressed_reads_l and args.output_suppressed_reads_r):
        additional_opts += ' --ambiguous '

    arguments.update( {'args': additional_opts, 'reads': reads} )

    # Final command:
    cmd = cmd % arguments

    # Run
    try:
        tmp_out = tempfile.NamedTemporaryFile().name
        tmp_stdout = open( tmp_out, 'wb' )
        tmp_err = tempfile.NamedTemporaryFile().name
        tmp_stderr = open( tmp_err, 'wb' )
        proc = subprocess.Popen( args=cmd, shell=True, cwd=".", stdout=tmp_stdout, stderr=tmp_stderr )
        returncode = proc.wait()
        tmp_stderr.close()
        # get stderr, allowing for case where it's very large
        tmp_stderr = open( tmp_err, 'rb' )
        stderr = ''
        buffsize = 1048576
        try:
            while True:
                stderr += tmp_stderr.read( buffsize )
                if not stderr or len( stderr ) % buffsize != 0:
                    break
        except OverflowError:
            pass
        tmp_stdout.close()
        tmp_stderr.close()
        if returncode != 0:
            raise Exception, stderr
            
        # TODO: look for errors in program output.
    except Exception, e:
        stop_err( 'Error in bismark:\n' + str( e ) ) 


    # collect and copy output files
    """
    if args.output_report_file:
        output_report_file = open(args.output_report_file, 'w+')
        for line in fileinput.input(glob( os.path.join( output_dir, '*.txt') )):
            output_report_file.write(line)
        output_report_file.close()
    """

    if args.output_suppressed_reads:
        shutil.move( glob(os.path.join( output_dir, '*ambiguous_reads.txt'))[0], args.output_suppressed_reads )
    if args.output_suppressed_reads_l:
        shutil.move( glob(os.path.join( output_dir, '*ambiguous_reads_1.txt'))[0], args.output_suppressed_reads_l )
    if args.output_suppressed_reads_r:
        shutil.move( glob(os.path.join( output_dir, '*ambiguous_reads_2.txt'))[0], args.output_suppressed_reads_r )

    if args.output_unmapped_reads:
        shutil.move( glob(os.path.join( output_dir, '*unmapped_reads.txt'))[0], args.output_unmapped_reads )
    if args.output_unmapped_reads_l:
        shutil.move( glob(os.path.join( output_dir, '*unmapped_reads_1.txt'))[0], args.output_unmapped_reads_l )
    if args.output_unmapped_reads_r:
        shutil.move( glob(os.path.join( output_dir, '*unmapped_reads_2.txt'))[0], args.output_unmapped_reads_r )

    shutil.move( glob( os.path.join( output_dir, '*.sam'))[0] , args.output)

    # Clean up temp dirs
    if args.own_file:
        if os.path.exists( tmp_index_dir ):
            shutil.rmtree( tmp_index_dir )
    if os.path.exists( tmp_bismark_dir ):
        shutil.rmtree( tmp_bismark_dir )

if __name__=="__main__": __main__()
