import os, sys

def prep_sqlite( prepped, args ):
    os.makedirs( 'amalgamation' )
    for file in ( 'sqlite3.h', 'sqlite3.c', 'sqlite3ext.h' ):
        os.rename( file, os.path.join( 'amalgamation', file ) )

# change back to the build dir
if os.path.dirname( sys.argv[0] ) != "":
    os.chdir( os.path.dirname( sys.argv[0] ) )

# find setuptools
sys.path.append( os.path.join( '..', '..', '..', 'lib' ) )
from scramble_lib import *

tag = get_tag() # get the tag

sqlite_version = ( tag.split( "_" ) )[1].replace('.','_')
sqlite_archive_base = os.path.join( archives, "sqlite-amalgamation-%s" % sqlite_version )
sqlite_archive = get_archive( sqlite_archive_base )

clean( ['amalgamation'] ) # clean up any existing stuff (could happen if you run scramble.py by hand)

unpack_dep( sqlite_archive, None, prep_sqlite, None )

# reset args for distutils
me = sys.argv[0]
sys.argv = [ me ]
sys.argv.append( "build_static" )
if tag is not None:
    sys.argv.append( "egg_info" )
    sys.argv.append( "--tag-build=%s" %tag )
sys.argv.append( "bdist_egg" )

# do it
execfile( "setup.py", globals(), locals() )
