import os, sys

# change back to the build dir
if os.path.dirname( sys.argv[0] ) != "":
    os.chdir( os.path.dirname( sys.argv[0] ) )

# find setuptools
sys.path.append( os.path.join( '..', '..', '..', 'lib' ) )
from scramble_lib import *

tag = get_tag() # get the tag
get_deps() # require any dependent eggs
clean() # clean up any existing stuff (could happen if you run scramble.py by hand)

# reset args for distutils
me = sys.argv[0]
sys.argv = [ me ]
sys.argv.append( "egg_info" )
if tag is not None:
    sys.argv.append( "--tag-build=%s" %tag )
# svn revision (if any) is handled directly in tag-build
sys.argv.append( "--no-svn-revision" )
sys.argv.append( "bdist_egg" )

# apply patches (if any)
apply_patches()

cc = get_solaris_compiler()
if cc == 'cc':
     os.environ['CFLAGS'] = '-xc99=all -D_X_OPEN_SOURCE=600 -D_XPG6=1'

# do it
execfile( "setup.py", globals(), locals() )
