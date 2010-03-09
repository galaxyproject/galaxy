import os, sys, shutil
from distutils.sysconfig import get_config_var

def prep_postgres( prepped, args ):

    pg_version = args['version']
    pg_srcdir = os.path.join( os.getcwd(), "postgresql-%s" % pg_version )

    # set up environment
    os.environ['CC'] = get_config_var('CC')
    os.environ['CFLAGS'] = get_config_var('CFLAGS')
    os.environ['LDFLAGS'] = get_config_var('LDFLAGS')

    if '-fPIC' not in os.environ['CFLAGS']:
        os.environ['CFLAGS'] += ' -fPIC'

    # run configure
    run( "./configure --prefix=%s/postgres --disable-dependency-tracking --enable-static --disable-shared --without-readline --with-thread-safety" % os.getcwd(),
        os.path.join( os.getcwd(), "postgresql-%s" % pg_version ),
        "Configuring postgres (./configure)" )

    # compile
    run( "make ../../src/include/utils/fmgroids.h", os.path.join( pg_srcdir, 'src', 'backend' ), "Compiling fmgroids.h (cd src/backend; make ../../src/include/utils/fmgroids.h)" )
    run( "make", os.path.join( pg_srcdir, 'src', 'interfaces', 'libpq' ), "Compiling libpq (cd src/interfaces/libpq; make)" )
    run( "make", os.path.join( pg_srcdir, 'src', 'bin', 'pg_config' ), "Compiling pg_config (cd src/bin/pg_config; make)" )

    # install
    run( "make install", os.path.join( pg_srcdir, 'src', 'interfaces', 'libpq' ), "Compiling libpq (cd src/interfaces/libpq; make install)" )
    run( "make install", os.path.join( pg_srcdir, 'src', 'bin', 'pg_config' ), "Compiling pg_config (cd src/bin/pg_config; make install)" )
    run( "make install", os.path.join( pg_srcdir, 'src', 'include' ), "Compiling pg_config (cd src/include; make install)" )

    # create prepped archive
    print "%s(): Creating prepped archive for future builds at:" % sys._getframe().f_code.co_name
    print " ", prepped
    compress( prepped,
           'postgres/bin',
           'postgres/include',
           'postgres/lib' )

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

    # localize setup.cfg
    if not os.path.exists( 'setup.cfg.orig' ):
        shutil.copy( 'setup.cfg', 'setup.cfg.orig' )
        f = open( 'setup.cfg', 'a' )
        f.write( '\npg_config=postgres/bin/pg_config\n' )
        f.write( '\nlibraries=crypt\n' )
        f.close()

    # tag
    me = sys.argv[0]
    sys.argv = [ me ]
    if tag is not None:
        sys.argv.append( "egg_info" )
        sys.argv.append( "--tag-build=%s" %tag )
    sys.argv.append( "bdist_egg" )

    # go
    execfile( "setup.py", globals(), locals() )
