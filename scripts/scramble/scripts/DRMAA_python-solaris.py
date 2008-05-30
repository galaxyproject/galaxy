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

# if our python is 64 bit, use 64 bit sge...
if sys.maxint < ( 2048 * 1024 * 1024 ):
    if sys.byteorder == 'big':
        arch = "sparc"
    else:
        arch = "x86"
else:
    if sys.byteorder == 'big':
        arch = "sparc64"
    else:
        arch = "amd64"
    if not "CFLAGS" in os.environ:
        os.environ["CFLAGS"] = ""
    os.environ["CFLAGS"] += " -m64"

# if we're using sun cc, drop the gcc -Wno-unused option
import distutils.sysconfig
cc = distutils.sysconfig.get_config_var('CC')
if os.popen( cc + ' --version 2>&1' ).read().strip().split('\n')[0].startswith('gcc'):
    compiler = 'gcc'
elif os.popen( cc + ' -V 2>&1' ).read().strip().split('\n')[0].startswith('cc: Sun C'):
    compiler = 'sun'
else:
    print "scramble(): Unable to determine compiler"
    sys.exit(1)

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
    elif line.startswith('SGE6_ARCH='):
        line = 'SGE6_ARCH="sol-%s"\n' % arch
    elif line.startswith('link_args ='):
        line = 'link_args = [ "-L%s" % os.path.join(SGE6_ROOT, "lib", SGE6_ARCH), "-Wl,-R%s" % os.path.join(SGE6_ROOT, "lib", SGE6_ARCH),  "-ldrmaa"  ]\n'
    if line == "                   + [ '-Wno-unused' ]\n":
        if compiler == 'sun':
            line = "                   #+ [ '-Wno-unused' ]\n"
    print >>o, line,
i.close()
o.close()

# go
me = sys.argv[0]
sys.argv = [ me ]
sys.argv.append( "bdist_egg" )
execfile( "setup.py", globals(), locals() )
