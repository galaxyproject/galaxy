import os, sys, subprocess, tarfile, shutil

def unpack_prebuilt_torque():
    if not os.access( TORQUE_BINARY_ARCHIVE, os.F_OK ):
        print "unpack_prebuilt_torque(): No binary archive of Torque available for this platform - will build it now"
        build_torque()
    else:
        print "unpack_prebuilt_torque(): Found a previously built Torque binary archive for this platform."
        print "unpack_prebuilt_torque(): To force Torque to be rebuilt, remove the archive:"
        print " ", TORQUE_BINARY_ARCHIVE
        t = tarfile.open( TORQUE_BINARY_ARCHIVE, "r" )
        for fn in t.getnames():
            t.extract( fn )
        t.close()

def build_torque():
    # download
    if not os.access( TORQUE_ARCHIVE, os.F_OK ):
        pkg_resources.require( "twill" )
        import twill.commands as tc
        import twill.errors as te
        try:
            print "build_torque(): Downloading Torque source archive from:"
            print " ", TORQUE_URL
            tc.go( TORQUE_URL )
            tc.code( 200 )
            tc.save_html( TORQUE_ARCHIVE )
        except te.TwillAssertionError, e:
            print "build_torque(): Unable to fetch Torque source archive from:"
            print " ", TORQUE_URL
            sys.exit( 1 )
    # untar
    print "build_torque(): Unpacking Torque source archive from:"
    print " ", TORQUE_ARCHIVE
    t = tarfile.open( TORQUE_ARCHIVE, "r" )
    for fn in t.getnames():
        t.extract( fn )
    t.close()
    # patch
    file = os.path.join( "torque-%s" %TORQUE_VERSION, "src", "include", "libpbs.h" )
    print "build_torque(): Patching", file
    if not os.access( "%s.orig" %file, os.F_OK ):
        shutil.copyfile( file, "%s.orig" %file )
    i = open( "%s.orig" %file, "r" )
    o = open( file, "w" )
    for line in i.readlines():
        if line == "#define NCONNECTS 5\n":
            line = "#define NCONNECTS 50\n"
        print >>o, line,
    i.close()
    o.close()
    # configure
    print "build_torque(): Running Torque configure script"
    p = subprocess.Popen( args = CONFIGURE, shell = True, cwd = os.path.join( os.getcwd(), "torque-%s" %TORQUE_VERSION) )
    r = p.wait()
    if r != 0:
        print "build_torque(): Torque configure script failed"
        sys.exit( 1 )
    # compile
    print "build_torque(): Building Torque (make)"
    p = subprocess.Popen( args = "make", shell = True, cwd = os.path.join( os.getcwd(), "torque-%s" %TORQUE_VERSION) )
    r = p.wait()
    if r != 0:
        print "build_torque(): Building Torque (make) failed"
        sys.exit( 1 )
    # install
    print "build_torque(): Installing Torque (make install_lib)"
    p = subprocess.Popen( args = "make install_lib", shell = True, cwd = os.path.join( os.getcwd(), "torque-%s" %TORQUE_VERSION) )
    r = p.wait()
    if r != 0:
        print "build_torque(): Installing Torque (make install_lib) failed"
        sys.exit( 1 )
    # pack
    print "build_torque(): Creating binary Torque archive for future builds of pbs_python"
    t = tarfile.open( TORQUE_BINARY_ARCHIVE, "w:bz2" )
    t.add( "torque" )
    t.close()

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

TORQUE_VERSION = ( tag.split( "_" ) )[1]
TORQUE_ARCHIVE = os.path.abspath( os.path.join( "..", "..", "..", "archives", "torque-%s.tar.gz" %TORQUE_VERSION ) )
TORQUE_BINARY_ARCHIVE = os.path.abspath( os.path.join( "..", "..", "..", "archives", "torque-%s-%s.tar.bz2" %( TORQUE_VERSION, pkg_resources.get_platform() ) ) )
TORQUE_URL = "http://www.clusterresources.com/downloads/torque/torque-%s.tar.gz" %TORQUE_VERSION
# there's no need to have a completely separate build script for this
if pkg_resources.get_platform() == "macosx-10.3-fat":
    CONFIGURE  = "CFLAGS='-O -g -isysroot /Developer/SDKs/MacOSX10.4u.sdk -arch i386 -arch ppc' "
    CONFIGURE += "LDFLAGS='-arch i386 -arch ppc' "
    CONFIGURE += "LD='gcc -mmacosx-version-min=10.4 -isysroot /Developer/SDKs/MacOSX10.4u.sdk -nostartfiles -arch i386 -arch ppc' "
    CONFIGURE += "./configure --prefix=%s/torque --disable-shared --disable-dependency-tracking --without-tcl --without-tk" %os.getcwd()
else:
    CONFIGURE = "CFLAGS='-fPIC' ./configure --prefix=%s/torque --disable-shared --without-tcl --without-tk" %os.getcwd()

# clean, in case you're running this by hand from a dirty module source dir
for dir in [ "build", "dist", "torque-%s" %TORQUE_VERSION ]:
    if os.access( dir, os.F_OK ):
        print "scramble_it.py: removing dir:", dir
        shutil.rmtree( dir )

# build/unpack Torque
unpack_prebuilt_torque()

print "scramble_it(): Running pbs_python configure script"
p = subprocess.Popen( args = "sh configure --with-pbsdir=torque/lib", shell = True )
r = p.wait()
if r != 0:
    print "scramble_it(): pbs_python configure script failed"
    sys.exit( 1 )

# version string in 2.9.4 setup.py is wrong
file = "setup.py"
print "scramble_it(): Patching", file
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
# need to change this to an extern declaration
file = os.path.join( "src", "log.h" )
print "build_torque(): Patching", file
if not os.access( "%s.orig" %file, os.F_OK ):
    shutil.copyfile( file, "%s.orig" %file )
i = open( "%s.orig" %file, "r" )
o = open( file, "w" )
for line in i.readlines():
    if line == 'char *msg_daemonname = "pbs_python";\n':
        line = 'extern char *msg_daemonname;\n'
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
