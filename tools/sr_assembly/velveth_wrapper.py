#!/usr/bin/env python

"""
Classes encapsulating decypher tool.
James E Johnson - University of Minnesota
"""
import pkg_resources
import logging, os, string, sys, tempfile, glob, shutil, types, urllib
import shlex, subprocess
from optparse import OptionParser, OptionGroup
from stat import *


log = logging.getLogger( __name__ )

assert sys.version_info[:2] >= ( 2, 4 )

def stop_err( msg ):
    sys.stderr.write( "%s\n" % msg )
    sys.exit()

def __main__():
    #Parse Command Line
    s = 'velveth_wrapper.py:  argv = %s\n' % (sys.argv)
    argcnt = len(sys.argv)
    html_file = sys.argv[1]
    working_dir = sys.argv[2]
    try: # for test - needs this done
        os.makedirs(working_dir)
    except Exception, e:
        stop_err( 'Error running velveth ' + str( e ) )
    hash_length = sys.argv[3]
    inputs = string.join(sys.argv[4:],' ')
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
            raise Exception, stderr
    except Exception, e:
        stop_err( 'Error running velveth ' + str( e ) )
    sequences_path = os.path.join(working_dir,'Sequences')
    roadmaps_path = os.path.join(working_dir,'Roadmaps')
    rval = ['<html><head><title>Velvet Galaxy Composite Dataset </title></head><p/>']
    rval.append('<div>%s<p/></div>' % (cmdline) )
    rval.append('<div>This composite dataset is composed of the following files:<p/><ul>')
    rval.append( '<li><a href="%s" type="text/plain">%s </a>%s</li>' % (sequences_path,'Sequences','Sequences' ) )
    rval.append( '<li><a href="%s" type="text/plain">%s </a>%s</li>' % (roadmaps_path,'Roadmaps','Roadmaps' ) )
    rval.append( '</ul></div></html>' )
    f = file(html_file,'w')
    f.write("\n".join( rval ))
    f.write('\n')
    f.close()

if __name__ == "__main__": __main__()
