import os, sys, shutil

if "SGE_ROOT" not in os.environ:
    print "scramble(): Please set SGE_ROOT to the path of your SGE installation"
    print "scramble(): before scrambling DRMAA_python"
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
for dir in [ "build", "dist", "gridengine" ]:
    if os.access( dir, os.F_OK ):
        print "scramble_it.py: removing dir:", dir
        shutil.rmtree( dir )

# patch
file = "setup.py"
print "scramble(): Patching", file
if not os.access( "%s.orig" %file, os.F_OK ):
    shutil.copyfile( file, "%s.orig" %file )
i = open( "%s.orig" %file, "r" )
o = open( file, "w" )
for line in i.readlines():
    if line == 'SGE6_ROOT="/scratch_test02/SGE6"\n':
        line = 'SGE6_ROOT="%s"\n' % os.environ["SGE_ROOT"]
    if line.startswith('link_args ='):
        line = 'link_args = [ "-L%s" % os.path.join(SGE6_ROOT, "lib", SGE6_ARCH), "-Wl,-R%s" % os.path.join(SGE6_ROOT, "lib", SGE6_ARCH),  "-ldrmaa"  ]\n'
    print >>o, line,
i.close()
o.close()

# go
me = sys.argv[0]
sys.argv = [ me ]
sys.argv.append( "bdist_egg" )
execfile( "setup.py", globals(), locals() )
