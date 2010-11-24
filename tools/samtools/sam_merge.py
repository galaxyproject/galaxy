#!/usr/bin/env python

"""
Merges any number of BAM files
usage: %prog [options]
    input1
    output1
    input2
    [input3[,input4[,input5[,...]]]]
"""

import os, subprocess, sys, tempfile

def stop_err( msg ):
    sys.stderr.write( '%s\n' % msg )
    sys.exit()

def __main__():
    infile =  sys.argv[1]
    outfile = sys.argv[2]
    if len( sys.argv ) < 3:
        stop_err( 'There are not enough files to merge' )
    filenames = sys.argv[3:]
    # output version # of tool
    try:
        tmp = tempfile.NamedTemporaryFile().name
        tmp_stdout = open( tmp, 'wb' )
        proc = subprocess.Popen( args='samtools 2>&1', shell=True, stdout=tmp_stdout )
        tmp_stdout.close()
        returncode = proc.wait()
        stdout = None
        for line in open( tmp_stdout.name, 'rb' ):
            if line.lower().find( 'version' ) >= 0:
                stdout = line.strip()
                break
        if stdout:
            sys.stdout.write( 'Samtools %s\n' % stdout )
        else:
            raise Exception
    except:
        sys.stdout.write( 'Could not determine Samtools version\n' )
    cmd = 'samtools merge %s %s %s' % ( outfile, infile, ' '.join( filenames ) )
    tmp = tempfile.NamedTemporaryFile().name
    try:
        tmp_stderr = open( tmp, 'wb' )
        proc = subprocess.Popen( args=cmd, shell=True, stderr=tmp_stderr.fileno() )
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
        if os.path.exists( tmp ):
            os.unlink( tmp )
    except Exception, e:
        if os.path.exists( tmp ):
            os.unlink( tmp )
        stop_err( 'Error running SAMtools merge tool\n' + str( e ) )
    if os.path.getsize( outfile ) > 0:
        sys.stdout.write( '%s files merged.' % ( len( sys.argv ) - 2 ) )
    else:
        stop_err( 'The output file is empty, there may be an error with one of your input files.' )

if __name__ == "__main__" : __main__()
