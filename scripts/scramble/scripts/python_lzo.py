import os, sys, subprocess, tarfile, shutil

def unpack_prebuilt_lzo():
    if not os.access( LZO_BINARY_ARCHIVE, os.F_OK ):
        print "unpack_prebuilt_lzo(): No binary archive of LZO available for this platform - will build it now"
        build_lzo()
    else:
        print "unpack_prebuilt_lzo(): Found a previously built LZO binary archive for this platform."
        print "unpack_prebuilt_lzo(): To force LZO to be rebuilt, remove the archive:"
        print " ", LZO_BINARY_ARCHIVE
        t = tarfile.open( LZO_BINARY_ARCHIVE, "r" )
        for fn in t.getnames():
            t.extract( fn )
        t.close()

def build_lzo():
    # untar
    print "build_lzo(): Unpacking LZO source archive from:"
    print " ", LZO_ARCHIVE
    t = tarfile.open( LZO_ARCHIVE, "r" )
    for fn in t.getnames():
        t.extract( fn )
    t.close()
    print "build_lzo(): Running LZO configure script"
    p = subprocess.Popen( args = CONFIGURE, shell = True, cwd = os.path.join( os.getcwd(), "lzo-%s" %LZO_VERSION) )
    r = p.wait()
    if r != 0:
        print "build_lzo(): LZO configure script failed"
        sys.exit( 1 )
    # compile
    print "build_lzo(): Building LZO (make)"
    p = subprocess.Popen( args = "make", shell = True, cwd = os.path.join( os.getcwd(), "lzo-%s" %LZO_VERSION) )
    r = p.wait()
    if r != 0:
        print "build_lzo(): Building LZO (make) failed"
        sys.exit( 1 )
    # install
    print "build_lzo(): Installing LZO (make install)"
    p = subprocess.Popen( args = "make install", shell = True, cwd = os.path.join( os.getcwd(), "lzo-%s" %LZO_VERSION) )
    r = p.wait()
    if r != 0:
        print "build_lzo(): Installing LZO (make install) failed"
        sys.exit( 1 )
    # pack
    print "build_lzo(): Creating binary LZO archive for future builds of psycopg2"
    t = tarfile.open( LZO_BINARY_ARCHIVE, "w:bz2" )
    t.add( "lzo" )
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

# LZO version is the same as this egg
LZO_VERSION = "1.08"
LZO_ARCHIVE = os.path.abspath( os.path.join( "..", "..", "..", "archives", "lzo-%s.tar.gz" %LZO_VERSION ) )
LZO_BINARY_ARCHIVE = os.path.abspath( os.path.join( "..", "..", "..", "archives", "lzo-%s-%s.tar.bz2" %( LZO_VERSION, pkg_resources.get_platform() ) ) )
# there's no need to have a completely separate build script for this
if pkg_resources.get_platform() == "macosx-10.3-fat":
    CONFIGURE  = "CFLAGS='-O -g -isysroot /Developer/SDKs/MacOSX10.4u.sdk -arch i386 -arch ppc' "
    CONFIGURE += "LDFLAGS='-arch i386 -arch ppc' "
    CONFIGURE += "LD='gcc -mmacosx-version-min=10.4 -isysroot /Developer/SDKs/MacOSX10.4u.sdk -nostartfiles -arch i386 -arch ppc' "
    CONFIGURE += "./configure --prefix=%s/lzo --disable-shared --disable-dependency-tracking --enable-static" %os.getcwd()
else:
    CONFIGURE = "CFLAGS='-fPIC' ./configure --prefix=%s/lzo --disable-shared --enable-static" %os.getcwd()

# clean, in case you're running this by hand from a dirty module source dir
for dir in [ "build", "dist", "lzo-%s" %LZO_VERSION ]:
    if os.access( dir, os.F_OK ):
        print "scramble_it.py: removing dir:", dir
        shutil.rmtree( dir )

# build/unpack LZO
unpack_prebuilt_lzo()

file = "setup.py"
print "build(): Patching", file
if not os.access( "%s.orig" %file, os.F_OK ):
    shutil.copyfile( file, "%s.orig" %file )
i = open( "%s.orig" %file, "r" )
o = open( file, "w" )
# probably should just make a search/replace dict
for line in i.readlines():
    if line == '    libraries = ["lzo"]\n':
        line = '    #libraries = ["lzo"]\n'
    elif line == 'include_dirs = []\n':
        line = 'include_dirs = ["lzo/include"]\n'
    elif line == 'library_dirs = []\n':
        line = 'library_dirs = ["lzo/lib"]\n'
        # linux has a separate crypt lib
    elif line == 'extra_compile_args = []\n':
        if not pkg_resources.get_platform().startswith( "macosx" ):
            line = 'extra_compile_args = ["-fPIC"]\n'
    elif line == 'extra_link_args = []\n':
        line = 'extra_link_args = ["lzo/lib/liblzo.a"]\n'
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
