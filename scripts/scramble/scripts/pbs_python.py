import os, sys, shutil, subprocess

if "LIBTORQUE_DIR" not in os.environ:
    print "scramble(): Please set LIBTORQUE_DIR to the path of the"
    print "scramble(): directory containing libtorque.so"
    sys.exit(1)

# change back to the build dir
if os.path.dirname( sys.argv[0] ) != "":
    os.chdir( os.path.dirname( sys.argv[0] ) )

# find setuptools
scramble_lib = os.path.join( "..", "..", "..", "lib" )
sys.path.append( scramble_lib )
import get_platform # fixes fat python 2.5
try:
    from setuptools import *
    import pkg_resources
except:
    from ez_setup import use_setuptools
    use_setuptools( download_delay=8, to_dir=scramble_lib )
    from setuptools import *
    import pkg_resources

# clean, in case you're running this by hand from a dirty module source dir
for dir in [ "build", "dist" ]:
    if os.access( dir, os.F_OK ):
        print "scramble(): removing dir:", dir
        shutil.rmtree( dir )

# the build process doesn't set an rpath for libtorque
os.environ['LD_RUN_PATH'] = os.environ['LIBTORQUE_DIR']

print "scramble(): Running pbs_python configure script"
p = subprocess.Popen( args = "sh configure --with-pbsdir=%s" % os.environ['LIBTORQUE_DIR'], shell = True )
r = p.wait()
if r != 0:
    print "scramble(): pbs_python configure script failed"
    sys.exit( 1 )

# version string in 2.9.4 setup.py is wrong
file = "setup.py"
print "scramble(): Patching", file
if not os.access( "%s.orig" %file, os.F_OK ):
    shutil.copyfile( file, "%s.orig" %file )
i = open( "%s.orig" %file, "r" )
o = open( file, "w" )
for line in i.readlines():
    if line == "	version = '2.9.0',\n":
        line = "	version = '2.9.4',\n"
    print >>o, line,
i.close()
o.close()

# tag
me = sys.argv[0]
sys.argv = [ me ]
sys.argv.append( "bdist_egg" )

# go
execfile( "setup.py", globals(), locals() )
