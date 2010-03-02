import os, sys, shutil

if "LIBTORQUE_DIR" not in os.environ:
    print "main(): Please set LIBTORQUE_DIR to the path of the"
    print "main(): directory containing libtorque.so"
    sys.exit(1)

# change back to the build dir
if os.path.dirname( sys.argv[0] ) != "":
    os.chdir( os.path.dirname( sys.argv[0] ) )

# find setuptools
sys.path.append( os.path.join( '..', '..', '..', 'lib' ) )
from scramble_lib import *

tag = get_tag() # get the tag
clean() # clean up any existing stuff (could happen if you run scramble.py by hand)

# the build process doesn't set an rpath for libtorque
os.environ['LD_RUN_PATH'] = os.environ['LIBTORQUE_DIR']

# run the config script
run( 'sh configure --with-pbsdir=%s' % os.environ['LIBTORQUE_DIR'], os.getcwd(), 'Running pbs_python configure script' )

# reset args for distutils
me = sys.argv[0]
sys.argv = [ me ]
sys.argv.append( "egg_info" )
if tag is not None:
    sys.argv.append( "--tag-build=%s" %tag )
# svn revision (if any) is handled directly in tag-build
sys.argv.append( "--no-svn-revision" )
sys.argv.append( "bdist_egg" )

# go
execfile( "setup.py", globals(), locals() )
