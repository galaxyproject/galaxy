#!/usr/bin/env python

"""
Classes encapsulating decypher tool.
James E Johnson - University of Minnesota
"""
import pkg_resources;
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
    s = 'velvetg_wrapper.py:  argv = %s\n' % (sys.argv)
    # print >> sys.stderr, s # so will appear as blurb for file
    argcnt = len(sys.argv)
    working_dir = sys.argv[1]
    contigs = sys.argv[2]
    stats = sys.argv[3]
    LastGraph = sys.argv[4]
    afgFile = sys.argv[5]
    unusedReadsFile = sys.argv[6]
    inputs = string.join(sys.argv[7:],' ')
    cmdline = 'velvetg %s %s > /dev/null' % (working_dir, inputs)
    # print >> sys.stderr, cmdline # so will appear as blurb for file
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
        stop_err( 'Error running velvetg ' + str( e ) )
    out = open(contigs,'w')
    contigs_path = os.path.join(working_dir,'contigs.fa')
    for line in open( contigs_path ):
        out.write( "%s" % (line) )
    out.close()
    out = open(stats,'w')
    stats_path = os.path.join(working_dir,'stats.txt')
    for line in open( stats_path ):
        out.write( "%s" % (line) )
    out.close()
    if LastGraph != 'None':
        out = open(LastGraph,'w')
        LastGraph_path = os.path.join(working_dir,'LastGraph')
        for line in open( LastGraph_path ):
            out.write( "%s" % (line) )
        out.close()
    if afgFile != 'None':
        out = open(afgFile,'w')
        afgFile_path = os.path.join(working_dir,'velvet_asm.afg')
        try:
            for line in open( afgFile_path ):
                out.write( "%s" % (line) )
        except:
            logging.warn( 'error reading %s' %(afgFile_path))
            pass
        out.close()
    if unusedReadsFile != 'None':
        out = open(unusedReadsFile,'w')
        unusedReadsFile_path = os.path.join(working_dir,'UnusedReads.fa')
        try:
            for line in open( unusedReadsFile_path ):
                out.write( "%s" % (line) )
        except:
            logging.info( 'error reading %s' %(unusedReadsFile_path))
            pass
        out.close()

if __name__ == "__main__": __main__()
