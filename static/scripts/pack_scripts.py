#!/usr/bin/env python

import sys, os

from glob import glob
from subprocess import call
from shutil import copyfile
from os import path

# Scripts that should not be packed -- just copied
do_not_pack = set()

cmd = "java -jar ../../scripts/yuicompressor.jar --type js %(fname)s -o packed/%(fname)s"
# cmd = "java -jar ../../scripts/compiler.jar --compilation_level SIMPLE_OPTIMIZATIONS --js %(fname)s --js_output_file packed/%(fname)s"

# If specific scripts specified on command line, just pack them, otherwise pack
# all.

def recursive_glob( pattern, excluded_dirs ):
    """
    Returns all items that match pattern in root and subdirectories.
    """
    
    a_dir, a_pattern = path.split( pattern )
    
    # Skip excluded dirs.
    if a_dir in excluded_dirs:
        return []
    
    # Search current dir.
    # print a_dir, a_pattern
    rval = glob( pattern )
    for item in glob( path.join( a_dir, "*" ) ):
        if path.isdir( item ):
            rval.extend( recursive_glob( path.join( item, a_pattern ), excluded_dirs ) )
    
    return rval

# Get files to pack.
if len( sys.argv ) > 1:
    to_pack = sys.argv[1:]
else:
    to_pack = recursive_glob( "*.js", [ "packed" ] )


for fname in to_pack:
    d = dict( fname=fname )
    packed_fname = path.join( 'packed', fname )
    
    # Only copy if full version is newer than packed version.
    if path.exists( packed_fname ) and ( path.getmtime( fname ) < path.getmtime( packed_fname ) ):
        print "Packed is current: %s" % fname
        continue
    
    print "%(fname)s --> packed/%(fname)s" % d
    
    # Create destination dir if necessary.
    dir, name = os.path.split( packed_fname )
    if not path.exists( dir ):
        print "Creating needed directory %s" % dir
        os.makedirs( dir )
    
    # Copy/pack.
    if fname in do_not_pack:
        copyfile( fname, path.join( packed_fname ) )
    else:
        out = call( cmd % d, shell=True )
