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
    parser.add_option( '', '--settings', dest='settings', help='' )

    (options, args) = parser.parse_args()

    # Creat bowtie index if necessary.
    tmp_index_dir = tempfile.mkdtemp()
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

    # Build bowtie command.
    cmd = 'bowtie2 %s -x %s %s -S %s'
    
    # Set up reads.
    if options.single_paired == 'paired':
        reads = " -1 %s -2 %s" % ( options.input1, options.input2 )
    else:
        reads = " -U %s" % ( options.input1 )
    
    # Set up options.
    opts = '-p %s' % ( options.num_threads )
    if options.settings == 'preSet':
        pass
    else:
        pass
        
    # Final command:
    cmd = cmd % ( opts, index_path, reads, options.output )
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

    # Clean up temp dirs
    if os.path.exists( tmp_index_dir ):
        shutil.rmtree( tmp_index_dir )

if __name__=="__main__": __main__()
