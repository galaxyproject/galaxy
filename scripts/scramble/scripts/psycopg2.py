import os, sys, subprocess, tarfile, shutil, glob
from distutils.sysconfig import get_config_var

def prep_postgres( prepped, args ):

    pg_version = args['version']
    if pkg_resources.get_platform().startswith('solaris'):
        make = 'gmake'
    else:
        make = 'make'

    # set up environment
    os.environ['CC'] = get_config_var('CC')
    os.environ['CFLAGS'] = get_config_var('CFLAGS')
    os.environ['LDFLAGS'] = get_config_var('LDFLAGS')

    # run configure (to generate pg_config.h)
    run( "./configure --without-readline",
        os.path.join( os.getcwd(), "postgresql-%s" % pg_version ),
        "Configuring postgres (./configure)" )

    # create src/port/pg_config_paths.h
    run( "%s pg_config_paths.h" % make,
        os.path.join( os.getcwd(), "postgresql-%s" % pg_version, "src", "port" ),
        "Creating postgresql-%s/src/port/pg_config_paths.h" % pg_version )

    # remove win32 crap in libpq dir
    for file in glob.glob( "postgresql-%s/src/interfaces/libpq/*win32*" % pg_version ):
        print "prep_postgres(): Removing %s" % file
        os.unlink( file )

    # create prepped archive
    print "%s(): Creating prepped archive for future builds at:" % sys._getframe().f_code.co_name
    print " ", prepped
    compress( prepped,
           "postgresql-%s/src/include" % pg_version,
           "postgresql-%s/src/port/pg_config_paths.h" % pg_version,
           "postgresql-%s/src/port/pgstrcasecmp.c" % pg_version,
           "postgresql-%s/src/backend/libpq/md5.c" % pg_version,
           "postgresql-%s/src/interfaces/libpq" % pg_version )

if __name__ == '__main__':

    # change back to the build dir
    if os.path.dirname( sys.argv[0] ) != "":
        os.chdir( os.path.dirname( sys.argv[0] ) )

    # find setuptools
    sys.path.append( os.path.abspath( os.path.join( '..', '..', '..', 'lib' ) ) )
    from scramble_lib import *

    tag = get_tag()

    pg_version = ( tag.split( "_" ) )[1]
    pg_archive_base = os.path.join( archives, "postgresql-%s" % pg_version )
    pg_archive = get_archive( pg_archive_base )
    pg_archive_prepped = os.path.join( archives, "postgresql-%s-%s.tar.gz" % ( pg_version, platform_noucs ) )

    # clean up any existing stuff (could happen if you run scramble.py by hand)
    clean( [ 'postgresql-%s' % pg_version ] )

    # unpack postgres
    unpack_dep( pg_archive, pg_archive_prepped, prep_postgres, dict( version=pg_version ) )

    # get setup.py
    shutil.copy( os.path.join( patches, 'psycopg2', 'setup.py' ), 'setup.py' )

    # tag
    me = sys.argv[0]
    sys.argv = [ me ]
    if tag is not None:
        sys.argv.append( "egg_info" )
        sys.argv.append( "--tag-build=%s" %tag )
    sys.argv.append( "bdist_egg" )

    # go
    execfile( "setup.py", globals(), locals() )
