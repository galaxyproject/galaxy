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
        print "scramble.py: removing dir:", dir
        shutil.rmtree( dir )

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

if not os.access( 'setup.py', os.F_OK ):
    print "scramble.py: Creating setup.py for GeneTrack"
    setup_py = """from os import walk
from os.path import join
from setuptools import setup, find_packages
def walk_files( top ):
    for dir, dirs, files in walk( top ):
        yield( dir, [ join( dir, f ) for f in files ] )
setup(
        name = "GeneTrack",
        version = "2.0.0-beta-1",
        packages = ['genetrack','genetrack.scripts'],
        data_files = [ f for f in walk_files('tests') ],
        zip_safe = False
)
"""
    open( 'setup.py', 'w' ).write( setup_py )


# do it
execfile( "setup.py", globals(), locals() )
