import os, sys, subprocess, tarfile, zipfile, shutil

def unpack_sqlite_source():
    if not os.access( SQLITE_ARCHIVE, os.F_OK ):
        print "unpack_sqlite_source(): No copy of sqlite source found in archives directory - fetching now"
        fetch_sqlite()
    else:
        print "unpack_sqlite_source(): Found a previously downloaded sqlite source."
        print "unpack_sqlite_source(): To force a new download, remove the archive:"
        print " ", SQLITE_ARCHIVE
    os.makedirs( "sqlite" )
    z = zipfile.ZipFile( SQLITE_ARCHIVE, "r" )
    for fn in z.namelist():
        if fn == "tclsqlite.c" or fn == "shell.c" or fn == "icu.c":
            continue
        o = open( os.path.join( "sqlite", fn ), "wb" )
        o.write( z.read( fn ) )
        o.close()
    z.close()

def fetch_sqlite():
    pkg_resources.require( "twill" )
    import twill.commands as tc
    import twill.errors as te
    try:
        print "fetch_sqlite(): Downloading sqlite source archive from:"
        print " ", SQLITE_URL
        tc.go( SQLITE_URL )
        tc.code( 200 )
        tc.save_html( SQLITE_ARCHIVE )
    except te.TwillAssertionError, e:
        print "fetch_sqlite(): Unable to fetch sqlite source archive from:"
        print " ", SQLITE_URL

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

SQLITE_VERSION = ( tag.split( "_" ) )[1]
SQLITE_ARCHIVE = os.path.abspath( os.path.join( "..", "..", "..", "archives", "sqlite-source-%s.zip" %SQLITE_VERSION.replace( ".", "_" ) ) )
SQLITE_URL = "http://www.sqlite.org/sqlite-source-%s.zip" %SQLITE_VERSION.replace( ".", "_" )

# clean, in case you're running this by hand from a dirty module source dir
for dir in [ "build", "dist", "sqlite" ]:
    if os.access( dir, os.F_OK ):
        print "scramble_it.py: removing dir:", dir
        shutil.rmtree( dir )

# build/unpack SQLite
unpack_sqlite_source()

# changes to setup.py
file = "setup.py"
print "build(): Patching", file
if not os.access( "%s.orig" %file, os.F_OK ):
    shutil.copyfile( file, "%s.orig" %file )
i = open( "%s.orig" %file, "r" )
o = open( file, "w" )
for line in i.readlines():
    if line == '           "src/util.c", "src/row.c"]\n':
        line += 'sources += glob.glob("./sqlite/*.c")\n'
    if line == "include_dirs = []\n":
        line = "include_dirs = [ './sqlite' ]\n"
    if line == "define_macros = []\n":
        line = "define_macros = [ ('THREADSAFE','1') ]\n"
    print >>o, line,
i.close()
o.close()

# don't want setup.cfg
os.rename( "setup.cfg", "setup.cfg.orig" )

# tag
me = sys.argv[0]
sys.argv = [ me ]
if tag is not None:
    sys.argv.append( "egg_info" )
    sys.argv.append( "--tag-build=%s" %tag )
sys.argv.append( "bdist_egg" )

# go
execfile( "setup.py", globals(), locals() )
