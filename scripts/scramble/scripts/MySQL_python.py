import os, sys, subprocess, tarfile, shutil

def unpack_prebuilt_mysql():
    if not os.access( MYSQL_BINARY_ARCHIVE, os.F_OK ):
        print "unpack_prebuilt_mysql(): No binary archive of MySQL available for this platform - will build it now"
        build_mysql()
    else:
        print "unpack_prebuilt_mysql(): Found a previously built MySQL binary archive for this platform."
        print "unpack_prebuilt_mysql(): To force MySQL to be rebuilt, remove the archive:"
        print " ", MYSQL_BINARY_ARCHIVE
        t = tarfile.open( MYSQL_BINARY_ARCHIVE, "r" )
        for fn in t.getnames():
            t.extract( fn )
        t.close()

def build_mysql():
    # untar
    print "build_mysql(): Unpacking mysql source archive from:"
    print " ", MYSQL_ARCHIVE
    t = tarfile.open( MYSQL_ARCHIVE, "r" )
    for fn in t.getnames():
        t.extract( fn )
    t.close()
    # configure
    print "build_mysql(): Running mysql configure script"
    p = subprocess.Popen( args = CONFIGURE, shell = True, cwd = os.path.join( os.getcwd(), "mysql-%s" %MYSQL_VERSION) )
    r = p.wait()
    if r != 0:
        print "build_mysql(): mysql configure script failed"
        sys.exit( 1 )
    # compile
    print "build_mysql(): Building mysql (make)"
    p = subprocess.Popen( args = "make", shell = True, cwd = os.path.join( os.getcwd(), "mysql-%s" %MYSQL_VERSION) )
    r = p.wait()
    if r != 0:
        print "build_mysql(): Building mysql (make) failed"
        sys.exit( 1 )
    # install
    print "build_mysql(): Installing mysql (make install)"
    p = subprocess.Popen( args = "make install", shell = True, cwd = os.path.join( os.getcwd(), "mysql-%s" %MYSQL_VERSION) )
    r = p.wait()
    if r != 0:
        print "build_mysql(): Installing mysql (make install) failed"
        sys.exit( 1 )
    # pack
    print "build_mysql(): Creating binary mysql archive for future builds of psycopg2"
    t = tarfile.open( MYSQL_BINARY_ARCHIVE, "w:bz2" )
    t.add( "mysql/bin/mysql_config" )
    t.add( "mysql/include" )
    t.add( "mysql/lib" )
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

# globals
MYSQL_VERSION = ( tag.split( "_" ) )[1]
MYSQL_ARCHIVE = os.path.abspath( os.path.join( "..", "..", "..", "archives", "mysql-%s.tar.gz" %MYSQL_VERSION ) )
MYSQL_BINARY_ARCHIVE = os.path.abspath( os.path.join( "..", "..", "..", "archives", "mysql-%s-%s.tar.bz2" %( MYSQL_VERSION, pkg_resources.get_platform() ) ) )
# there's no need to have a completely separate build script for this
if pkg_resources.get_platform() == "macosx-10.3-fat":
    CONFIGURE  = "CFLAGS='-O -g -isysroot /Developer/SDKs/MacOSX10.4u.sdk -arch i386 -arch ppc' "
    CONFIGURE += "CXXFLAGS='-O -g -isysroot /Developer/SDKs/MacOSX10.4u.sdk -arch i386 -arch ppc' "
    CONFIGURE += "LDFLAGS='-arch i386 -arch ppc' "
    CONFIGURE += "LD='gcc -mmacosx-version-min=10.4 -isysroot /Developer/SDKs/MacOSX10.4u.sdk -nostartfiles -arch i386 -arch ppc' "
    CONFIGURE += "./configure --prefix=%s/mysql --disable-dependency-tracking --without-server --without-uca --without-libwrap " %os.getcwd()
    CONFIGURE += "--without-extra-tools --without-openssl --without-yassl --without-docs --without-man --without-bench --enable-thread-safe-client"
else:
    CONFIGURE  = "CFLAGS='-fPIC' ./configure --prefix=%s/mysql --disable-shared --without-server --without-uca --without-libwrap " %os.getcwd()
    CONFIGURE += "--without-extra-tools --without-openssl --without-yassl --without-docs --without-man --without-bench --enable-thread-safe-client"

# clean, in case you're running this by hand from a dirty module source dir
for dir in [ "build", "dist", "mysql-%s" %MYSQL_VERSION ]:
    if os.access( dir, os.F_OK ):
        print "scramble_it.py: removing dir:", dir
        shutil.rmtree( dir )

# build/unpack MySQL
unpack_prebuilt_mysql()

# patch
file = "site.cfg"
print "scramble_it(): Patching", file
if not os.access( "%s.orig" %file, os.F_OK ):
    shutil.copyfile( file, "%s.orig" %file )
i = open( "%s.orig" %file, "r" )
o = open( file, "w" )
for line in i.readlines():
    if line == "#mysql_config = /usr/local/bin/mysql_config\n":
        line = "mysql_config = mysql/bin/mysql_config\n"
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
