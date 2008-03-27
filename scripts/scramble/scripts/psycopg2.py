import os, sys, subprocess, tarfile, shutil

def unpack_prebuilt_postgres():
    if not os.access( POSTGRES_BINARY_ARCHIVE, os.F_OK ):
        print "unpack_prebuilt_postgres(): No binary archive of Postgres available for this platform - will build it now"
        build_postgres()
    else:
        print "unpack_prebuilt_postgres(): Found a previously built Postgres binary archive for this platform."
        print "unpack_prebuilt_postgres(): To force Postgres to be rebuilt, remove the archive:"
        print " ", POSTGRES_BINARY_ARCHIVE
        t = tarfile.open( POSTGRES_BINARY_ARCHIVE, "r" )
        for fn in t.getnames():
            t.extract( fn )
        t.close()

def build_postgres():
    # download
    if not os.access( POSTGRES_ARCHIVE, os.F_OK ):
        pkg_resources.require( "twill" )
        import twill.commands as tc
        import twill.errors as te
        try:
            print "build_postgres(): Downloading postgres source archive from:"
            print " ", POSTGRES_URL
            tc.go( POSTGRES_URL )
            tc.code( 200 )
            tc.save_html( POSTGRES_ARCHIVE )
        except te.TwillAssertionError, e:
            print "build_postgres(): Unable to fetch postgres source archive from:"
            print " ", POSTGRES_URL
            sys.exit( 1 )
    # untar
    print "build_postgres(): Unpacking postgres source archive from:"
    print " ", POSTGRES_ARCHIVE
    t = tarfile.open( POSTGRES_ARCHIVE, "r" )
    for fn in t.getnames():
        t.extract( fn )
    t.close()
    # configure
    print "build_postgres(): Running postgres configure script"
    p = subprocess.Popen( args = CONFIGURE, shell = True, cwd = os.path.join( os.getcwd(), "postgresql-%s" %POSTGRES_VERSION) )
    r = p.wait()
    if r != 0:
        print "build_postgres(): postgres configure script failed"
        sys.exit( 1 )
    # compile
    print "build_postgres(): Building postgres (make)"
    p = subprocess.Popen( args = "make", shell = True, cwd = os.path.join( os.getcwd(), "postgresql-%s" %POSTGRES_VERSION) )
    r = p.wait()
    if r != 0:
        print "build_postgres(): Building postgres (make) failed"
        sys.exit( 1 )
    # install
    print "build_postgres(): Installing postgres (make install)"
    p = subprocess.Popen( args = "make install", shell = True, cwd = os.path.join( os.getcwd(), "postgresql-%s" %POSTGRES_VERSION) )
    r = p.wait()
    if r != 0:
        print "build_postgres(): Installing postgres (make install) failed"
        sys.exit( 1 )
    # pack
    print "build_postgres(): Creating binary postgres archive for future builds of psycopg2"
    t = tarfile.open( POSTGRES_BINARY_ARCHIVE, "w:bz2" )
    t.add( "postgres/bin/pg_config" )
    t.add( "postgres/include" )
    t.add( "postgres/lib" )
    t.close()
    # remove self-referencing symlink
    os.unlink( os.path.join( "postgresql-%s" %POSTGRES_VERSION, "src", "test", "regress", "regress.so" ) )

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

POSTGRES_VERSION = ( tag.split( "_" ) )[1]
POSTGRES_ARCHIVE = os.path.abspath( os.path.join( "..", "..", "..", "archives", "postgresql-%s.tar.bz2" %POSTGRES_VERSION ) )
POSTGRES_BINARY_ARCHIVE = os.path.abspath( os.path.join( "..", "..", "..", "archives", "postgresql-%s-%s.tar.bz2" %( POSTGRES_VERSION, pkg_resources.get_platform() ) ) )
POSTGRES_URL = "http://ftp8.us.postgresql.org/postgresql/source/v%s/postgresql-%s.tar.bz2" %( POSTGRES_VERSION, POSTGRES_VERSION )
# there's no need to have a completely separate build script for this
if pkg_resources.get_platform() == "macosx-10.3-fat":
    CONFIGURE = "CFLAGS='-O -g -isysroot /Developer/SDKs/MacOSX10.4u.sdk -arch i386 -arch ppc' LDFLAGS='-arch i386 -arch ppc' LD='gcc -mmacosx-version-min=10.4 -isysroot /Developer/SDKs/MacOSX10.4u.sdk -nostartfiles -arch i386 -arch ppc' ./configure --prefix=%s/postgres --disable-shared --disable-dependency-tracking --without-readline" %os.getcwd()
else:
    CONFIGURE = "CFLAGS='-fPIC' ./configure --prefix=%s/postgres --disable-shared --without-readline" %os.getcwd()

# clean, in case you're running this by hand from a dirty module source dir
for dir in [ "build", "dist", "postgresql-%s" %POSTGRES_VERSION ]:
    if os.access( dir, os.F_OK ):
        print "scramble_it.py: removing dir:", dir
        shutil.rmtree( dir )

# build/unpack Postgres
unpack_prebuilt_postgres()

# patch
file = "setup.cfg"
print "build(): Patching", file
if not os.access( "%s.orig" %file, os.F_OK ):
    shutil.copyfile( file, "%s.orig" %file )
i = open( "%s.orig" %file, "r" )
o = open( file, "w" )
for line in i.readlines():
    if line == "#pg_config=\n":
        line = "pg_config=postgres/bin/pg_config\n"
    if line == "#libraries=\n":
        # linux has a separate crypt lib
        if pkg_resources.get_platform().startswith( "linux" ):
            line = "libraries=crypt\n"
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
