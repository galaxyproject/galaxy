#!/usr/bin/env python

from glob import glob
from subprocess import call
from shutil import copyfile
from os import path

# Scripts that should not be packed
do_not_pack = set( [ "ie_pngfix.js", "aflax.js" ] )

cmd = "java -jar ../../scripts/yuicompressor.jar --warn %(fname)s > packed/%(fname)s"

for fname in glob( "*.js" ):
    d = dict( fname=fname )
    print "%(fname)s --> packed/%(fname)s" % d
    if fname in do_not_pack:
        copyfile( fname, path.join( 'packed', fname ) )
    else:
        out = call( cmd % d, shell=True )
