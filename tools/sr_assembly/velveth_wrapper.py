#!/usr/bin/env python
"""
Classes encapsulating decypher tool.
James E Johnson - University of Minnesota
"""
import os
import string
import subprocess
import sys

assert sys.version_info[:2] >= ( 2, 4 )


def stop_err( msg ):
    sys.stderr.write( "%s\n" % msg )
    sys.exit()


def __main__():
    # Parse command line
    html_file = sys.argv[1]
    working_dir = sys.argv[2]
    try:  # for test - needs this done
        os.makedirs(working_dir)
    except Exception as e:
        stop_err( 'Error running velveth ' + str( e ) )
    hash_length = sys.argv[3]
    inputs = string.join(sys.argv[4:], ' ')
    cmdline = 'velveth %s %s %s > /dev/null' % (working_dir, hash_length, inputs)
    try:
        proc = subprocess.Popen( args=cmdline, shell=True, stderr=subprocess.PIPE )
        returncode = proc.wait()
        # get stderr, allowing for case where it's very large
        stderr = ''
        buffsize = 1048576
        try:
            while True:
                stderr += proc.stderr.read( buffsize )
                if not stderr or len( stderr ) % buffsize != 0:
                    break
        except OverflowError:
            pass
        if returncode != 0:
            raise Exception(stderr)
    except Exception as e:
        stop_err( 'Error running velveth ' + str( e ) )
    sequences_path = os.path.join(working_dir, 'Sequences')
    roadmaps_path = os.path.join(working_dir, 'Roadmaps')
    rval = ['<html><head><title>Velvet Galaxy Composite Dataset </title></head><p/>']
    rval.append('<div>%s<p/></div>' % (cmdline) )
    rval.append('<div>This composite dataset is composed of the following files:<p/><ul>')
    rval.append( '<li><a href="%s" type="text/plain">%s </a>%s</li>' % (sequences_path, 'Sequences', 'Sequences' ) )
    rval.append( '<li><a href="%s" type="text/plain">%s </a>%s</li>' % (roadmaps_path, 'Roadmaps', 'Roadmaps' ) )
    rval.append( '</ul></div></html>' )
    with open(html_file, 'w') as f:
        f.write("\n".join( rval ))
        f.write('\n')


if __name__ == "__main__":
    __main__()
