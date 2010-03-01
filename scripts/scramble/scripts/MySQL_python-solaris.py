import os, sys, shutil
from distutils.sysconfig import get_config_var

def prep_mysql( prepped, args ):

    my_version = args['version']
    my_srcdir = os.path.join( os.getcwd(), "mysql-%s" % my_version )

    # set up environment
    os.environ['CC'] = get_config_var('CC')
    os.environ['CFLAGS'] = get_config_var('CFLAGS')
    os.environ['LDFLAGS'] = get_config_var('LDFLAGS')

    cc = get_solaris_compiler()
    if cc == 'cc':
        os.environ['CFLAGS'] += ' -KPIC'
    elif cc == 'gcc':
        os.environ['CFLAGS'] += ' -fPIC -DPIC'

    # run configure
    run( "./configure --prefix=%s/mysql --disable-dependency-tracking --enable-static --disable-shared --without-server --without-uca " %os.getcwd() + \
         "--without-libwrap --without-ssl --without-docs --without-man --enable-thread-safe-client --with-named-curses-libs=''",
         my_srcdir, "Configuring mysql (./configure)" )

    # compile
    run( "make", os.path.join( my_srcdir, 'include' ), "Preparing mysql includes (cd include; make)" )
    run( "make link_sources", os.path.join( my_srcdir, 'libmysql' ), "Preparing libmysql (cd libmysql; make link_sources)" )
    run( "make link_sources", os.path.join( my_srcdir, 'libmysql_r' ), "Preparing libmysql_r (cd libmysql_r; make link_sources)" )
    run( "make", os.path.join( my_srcdir, 'libmysql_r' ), "Compiling libmysql_r (cd libmysql_r; make)" )
    run( "make", os.path.join( my_srcdir, 'scripts' ), "Preparing scripts (cd scripts; make)" )

    # install
    run( "make install", os.path.join( my_srcdir, 'include' ), "Installing mysql includes (cd include; make install)" )
    run( "make install", os.path.join( my_srcdir, 'libmysql_r' ), "Installing libmysql_r (cd libmysql_r; make install)" )
    run( "make install", os.path.join( my_srcdir, 'scripts' ), "Installing mysql scripts (cd scripts; make install)" )
    shutil.copy( os.path.join( my_srcdir, 'include', 'mysqld_error.h' ), os.path.join( 'mysql', 'include', 'mysql' ) )

    # create prepped archive
    print "%s(): Creating prepped archive for future builds at:" % sys._getframe().f_code.co_name
    print " ", prepped
    compress( prepped,
           'mysql/bin/mysql_config',
           'mysql/include',
           'mysql/lib' )

if __name__ == '__main__':

    # change back to the build dir
    if os.path.dirname( sys.argv[0] ) != "":
        os.chdir( os.path.dirname( sys.argv[0] ) )

    # find setuptools
    sys.path.append( os.path.abspath( os.path.join( '..', '..', '..', 'lib' ) ) )
    from scramble_lib import *

    tag = get_tag()

    my_version = ( tag.split( '_' ) )[1]
    my_archive_base = os.path.join( archives, 'mysql-%s' % my_version )
    my_archive = get_archive( my_archive_base )
    my_archive_prepped = os.path.join( archives, 'mysql-%s-%s.tar.gz' % ( my_version, platform_noucs ) )

    # clean up any existing stuff (could happen if you run scramble.py by hand)
    clean( [ 'mysql-%s' % my_version, 'mysql' ] )

    # unpack mysql
    unpack_dep( my_archive, my_archive_prepped, prep_mysql, dict( version=my_version ) )

    # get site.cfg
    shutil.copy( os.path.join( patches, 'MySQL_python', 'site.cfg' ), 'site.cfg' )

    # tag
    me = sys.argv[0]
    sys.argv = [ me ]
    if tag is not None:
        sys.argv.append( "egg_info" )
        sys.argv.append( "--tag-build=%s" %tag )
    sys.argv.append( "bdist_egg" )

    # go
    execfile( "setup.py", globals(), locals() )
