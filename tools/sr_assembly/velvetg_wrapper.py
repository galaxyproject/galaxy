#!/usr/bin/env python
"""
Classes encapsulating decypher tool.
James E Johnson - University of Minnesota
"""
from __future__ import print_function

import os
import subprocess
import sys

assert sys.version_info[:2] >= ( 2, 4 )


def stop_err( msg ):
    sys.stderr.write( "%s\n" % msg )
    sys.exit()


def __main__():
    # Parse Command Line
    working_dir = sys.argv[1]
    inputs = ' '.join(sys.argv[2:])
    for _ in ('Roadmaps', 'Sequences'):
        os.symlink(os.path.join(working_dir, _), _)
    cmdline = 'velvetg . %s' % (inputs)
    print("Command to be executed: %s" % cmdline)
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
        stop_err( 'Error running velvetg ' + str( e ) )


if __name__ == "__main__":
    __main__()
