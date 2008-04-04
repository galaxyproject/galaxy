import os, sys, shutil

# change back to the build dir
if os.path.dirname( sys.argv[0] ) != "":
    os.chdir( os.path.dirname( sys.argv[0] ) )

# find setuptools
scramble_lib = os.path.join( "..", "..", "..", "lib" )
sys.path.append( scramble_lib )
from ez_setup import use_setuptools
use_setuptools( download_delay=8, to_dir=scramble_lib )
from setuptools import *

# get the tag
if os.access( ".galaxy_tag", os.F_OK ):
    tagfile = open( ".galaxy_tag", "r" )
    tag = tagfile.readline().strip()
else:
    tag = None

# in case you're running this by hand from a dirty module source dir
for dir in [ "build", "dist" ]:
    if os.access( dir, os.F_OK ):
        print "scramble_it.py: removing dir:", dir
        shutil.rmtree( dir )

# patch
for file in [ "src/NameMapper.py", "src/Tests/NameMapper.py" ]:
    if not os.access( "%s.orig" %file, os.F_OK ):
        print "scramble_it(): Patching", file
        shutil.copyfile( file, "%s.orig" %file )
        i = open( "%s.orig" %file, "r" )
        o = open( file, "w" )
        for line in i.readlines():
            if line.startswith("__author__ ="):
                print >>o, "from __future__ import generators"
            elif line == "from __future__ import generators\n":
                continue
            print >>o, line,
        i.close()
        o.close()

# reset args for distutils
me = sys.argv[0]
sys.argv = [ me ]
sys.argv.append( "egg_info" )
if tag is not None:
    #sys.argv.append( "egg_info" )
    sys.argv.append( "--tag-build=%s" %tag )
# svn revision (if any) is handled directly in tag-build
sys.argv.append( "--no-svn-revision" )
sys.argv.append( "bdist_egg" )

# do it
execfile( "setup.py", globals(), locals() )
