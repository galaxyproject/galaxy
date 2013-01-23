#!/usr/bin/env python

import optparse, os, shutil, subprocess, sys, tempfile, fileinput

def stop_err( msg ):
    sys.stderr.write( "%s\n" % msg )
    sys.exit()

def __main__():
    #Parse Command Line
    parser = optparse.OptionParser()
    parser.add_option( '-p', '--num-threads', dest='num_threads', help='Use this many threads to align reads. The default is 1.' )
    parser.add_option( '', '--own-file', dest='own_file', help='' )
    parser.add_option( '-D', '--indexes-path', dest='index_path', help='Indexes directory; location of .ebwt and .fa files.' )

    # Wrapper options.
    parser.add_option( '-O', '--output', dest='output' )
    parser.add_option( '-1', '--input1', dest='input1', help='The (forward or single-end) reads file in Sanger FASTQ format' )
    parser.add_option( '-2', '--input2', dest='input2', help='The reverse reads file in Sanger FASTQ format' )
    parser.add_option( '', '--single-paired', dest='single_paired', help='' )
    parser.add_option( '-I', '--minins', dest='min_insert' )
    parser.add_option( '-X', '--maxins', dest='max_insert' )
    parser.add_option( '', '--settings', dest='settings', help='' )
    parser.add_option( '', '--end-to-end', dest='end_to_end', action="store_true" )
    parser.add_option( '', '--local', dest='local', action="store_true" )
    parser.add_option( '', '--preset-alignment', dest='preset_alignment')

    # Read group options.
    parser.add_option( '', '--rgid', dest='rgid', help='Read group identifier' )
    parser.add_option( '', '--rglb', dest='rglb', help='Library name' )
    parser.add_option( '', '--rgpl', dest='rgpl', help='Platform/technology used to produce the reads' )
    parser.add_option( '', '--rgsm', dest='rgsm', help='Sample' )

    parser.add_option( '', '--output_unaligned_reads', dest='output_unaligned_reads', help='File name for unaligned reads (single-end)' )
    parser.add_option( '', '--output_unaligned_reads_l', dest='output_unaligned_reads_l', help='File name for unaligned reads (left, paired-end)' )
    parser.add_option( '', '--output_unaligned_reads_r', dest='output_unaligned_reads_r', help='File name for unaligned reads (right, paired-end)' )

    (options, args) = parser.parse_args()
    
    tmp_unaligned_file_name = None
    # Creat bowtie index if necessary.
    tmp_index_dir = tempfile.mkdtemp()
    
    if options.single_paired == 'paired':
        if options.output_unaligned_reads_l and options.output_unaligned_reads_r:
            tmp_unaligned_file = tempfile.NamedTemporaryFile( dir=tmp_index_dir, suffix='.fastq' )
            tmp_unaligned_file_name = tmp_unaligned_file.name
            tmp_unaligned_file.close()
            output_unaligned_reads = '--un-conc %s' % tmp_unaligned_file_name
        else:
            output_unaligned_reads = ''
    elif options.output_unaligned_reads:
        output_unaligned_reads = '--un %s' % options.output_unaligned_reads
    else:
        output_unaligned_reads = ''
    
    if options.own_file:
        index_path = os.path.join( tmp_index_dir, '.'.join( os.path.split( options.own_file )[1].split( '.' )[:-1] ) )
        try:
            os.link( options.own_file, index_path + '.fa' )
        except:
            # Bowtie prefers (but doesn't require) fasta file to be in same directory, with .fa extension
            pass
        cmd_index = 'bowtie2-build -f %s %s' % ( options.own_file, index_path )
        try:
            tmp = tempfile.NamedTemporaryFile( dir=tmp_index_dir ).name
            tmp_stderr = open( tmp, 'wb' )
            proc = subprocess.Popen( args=cmd_index, shell=True, cwd=tmp_index_dir, stderr=tmp_stderr.fileno() )
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
    else:
        index_path = options.index_path

    # Build bowtie command; use view and sort to create sorted bam.
    cmd = 'bowtie2 %s -x %s %s %s | samtools view -Su - | samtools sort -o - - > %s'
    
    # Set up reads.
    if options.single_paired == 'paired':
        reads = " -1 %s -2 %s" % ( options.input1, options.input2 )
    else:
        reads = " -U %s" % ( options.input1 )
    
    # Set up options.
    opts = '-p %s' % ( options.num_threads )
    if options.single_paired == 'paired':
        if options.min_insert:
            opts += ' -I %s' % options.min_insert
        if options.max_insert:
            opts += ' -X %s' % options.max_insert
    if options.settings == 'preSet':
        pass
    else:
        if options.local:
            opts += ' --local'
        if options.preset_alignment:
            opts += ' --' + options.preset_alignment

    # Read group options.
    if options.rgid:
        if not options.rglb or not options.rgpl or not options.rgsm:
            stop_err( 'If you want to specify read groups, you must include the ID, LB, PL, and SM tags.' )
        opts += ' --rg-id %s' % options.rgid
        opts += ' --rg %s:%s' % ( 'LB', options.rglb )
        opts += ' --rg %s:%s' % ( 'PL', options.rgpl )
        opts += ' --rg %s:%s' % ( 'SM', options.rgsm )
        
    # Final command:
    cmd = cmd % ( opts, index_path, reads, output_unaligned_reads, options.output )
    print cmd

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
        stop_err( 'Error in bowtie2:\n' + str( e ) ) 

    # get unaligned reads output files in place if appropriate
    if options.single_paired == 'paired' and tmp_unaligned_file_name and options.output_unaligned_reads_l and options.output_unaligned_reads_r:
        try:
            left = tmp_unaligned_file_name.replace( '.fastq', '.1.fastq' )
            right = tmp_unaligned_file_name.replace( '.fastq', '.2.fastq' )
            shutil.move( left, options.output_unaligned_reads_l )
            shutil.move( right, options.output_unaligned_reads_r )
        except Exception, e:
            sys.stdout.write( 'Error producing the unaligned output files.\n' )

    # Clean up temp dirs
    if os.path.exists( tmp_index_dir ):
        shutil.rmtree( tmp_index_dir )

if __name__=="__main__": __main__()
