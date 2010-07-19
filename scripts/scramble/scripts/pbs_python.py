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

# version string in 2.9.4 setup.py is wrong
print "scramble(): Patching setup.py"
if not os.path.exists( 'setup.py.orig' ):
    shutil.copyfile( 'setup.py', 'setup.py.orig' )
    i = open( 'setup.py.orig', 'r' )
    o = open( 'setup.py', 'w' )
    for line in i.readlines():
        if line == "	version = '4.0.0',\n":
            line = "	version = '4.1.0',\n"
        print >>o, line,
i.close()
o.close()

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
