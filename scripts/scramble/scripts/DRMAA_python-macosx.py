import os, sys, subprocess, tarfile, shutil, urllib2

def unpack_sge():
    os.makedirs( "gridengine" )
    for file in [ SGE_COMMON_ARCHIVE, SGE_BINARY_PPC_ARCHIVE, SGE_BINARY_X86_ARCHIVE ]:
        if not os.access( file, os.F_OK ):
            fetch( file )
        t = tarfile.open( file, "r" )
        print "unpack_sge() Unpacking:"
        print " ", file
        for fn in t.getnames():
            t.extract( fn, "gridengine" )
        t.close()

def lipo():
    darwin_dir = os.path.join( "gridengine", "lib", "darwin" )
    os.rename( "%s-ppc" % darwin_dir, "%s-ppc.orig" % darwin_dir )
    os.rename( "%s-x86" % darwin_dir, "%s-x86.orig" % darwin_dir )
    os.makedirs( darwin_dir )
    os.symlink( "darwin", "%s-ppc" % darwin_dir )
    os.symlink( "darwin", "%s-x86" % darwin_dir )
    ppc_libdrmaa = os.path.join( "%s-ppc.orig" % darwin_dir, "libdrmaa.dylib.1.0" )
    x86_libdrmaa = os.path.join( "%s-x86.orig" % darwin_dir, "libdrmaa.dylib.1.0" )
    fat_libdrmaa = os.path.join( darwin_dir, "libdrmaa.dylib.1.0" )
    lipo_cmd = "lipo %s %s -create -output %s" % ( ppc_libdrmaa, x86_libdrmaa, fat_libdrmaa )
    os.symlink( "libdrmaa.dylib.1.0", os.path.join( darwin_dir, "libdrmaa.dylib" ) )
    p = subprocess.Popen( args = lipo_cmd, shell = True )
    r = p.wait()
    if r != 0:
        print "lipo(): lipo failed"
        sys.exit( 1 )

def fetch( file ):
    url = SGE_BASE_URL + os.path.basename( file )
    print "fetch(): Fetching:"
    print " ", url
    inf = urllib2.urlopen( url )
    otf = open( file, 'wb' )
    otf.write( inf.read() )
    inf.close()
    otf.close()

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

# get the tag
if os.access( ".galaxy_tag", os.F_OK ):
    tagfile = open( ".galaxy_tag", "r" )
    tag = tagfile.readline().strip()
else:
    tag = None

SGE_VERSION = ( tag.split( "_" ) )[1]
SGE_BASE_URL = "http://gridengine.sunsource.net/download/SGE61/"
SGE_COMMON_ARCHIVE = os.path.abspath( os.path.join( "..", "..", "..", "archives", "ge-%s-common.tar.gz" %SGE_VERSION ) )
SGE_BINARY_PPC_ARCHIVE = os.path.abspath( os.path.join( "..", "..", "..", "archives", "ge-%s-bin-darwin-ppc.tar.gz" % SGE_VERSION ) )
SGE_BINARY_X86_ARCHIVE = os.path.abspath( os.path.join( "..", "..", "..", "archives", "ge-%s-bin-darwin-x86.tar.gz" % SGE_VERSION ) )

# clean, in case you're running this by hand from a dirty module source dir
for dir in [ "build", "dist", "gridengine" ]:
    if os.access( dir, os.F_OK ):
        print "scramble_it.py: removing dir:", dir
        shutil.rmtree( dir )

# build/unpack SGE
unpack_sge()
lipo()

file = "setup.py"
print "scramble(): Patching", file
if not os.access( "%s.orig" %file, os.F_OK ):
    shutil.copyfile( file, "%s.orig" %file )
i = open( "%s.orig" %file, "r" )
o = open( file, "w" )
for line in i.readlines():
    if line == 'SGE6_ROOT="/scratch_test02/SGE6"\n':
        line = 'SGE6_ROOT="gridengine"\n'
    print >>o, line,
i.close()
o.close()

# tag
me = sys.argv[0]
sys.argv = [ me ]
if tag is not None:
    sys.argv.append( "egg_info" )
    sys.argv.append( "--tag-build=%s" %tag )
sys.argv.append( "bdist_egg" )

# go
execfile( "setup.py", globals(), locals() )
