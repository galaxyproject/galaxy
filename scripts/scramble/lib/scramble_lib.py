"""
Various utilities for scrambling.
"""
import os, sys, errno, re, distutils.util, glob, shutil, subprocess, tarfile, zipfile
from distutils.sysconfig import get_config_var, get_config_vars

try:
    import zlib
except:
    raise Exception( 'Cannot import zlib, which must exist to build eggs.  If your python interpreter is truly missing it, you will need to recompile or (on supported platforms) download a binary version from python.org.' )

def get_tag():
    try:
        return open( '.galaxy_tag', 'r' ).read().strip()
    except:
        return None

def get_ver():
    try:
        return open( '.galaxy_ver', 'r' ).read().strip()
    except:
        return None

def get_deps():
    try:
        depf = open( '.galaxy_deps', 'r' )
    except:
        return []
    c = eggs.Crate( None )
    for dep in depf:
        c[dep.strip()].require()

def clean( extra_dirs=[] ):
    for dir in [ 'build', 'dist' ] + extra_dirs:
        try:
            shutil.rmtree( dir )
        except OSError, e:
            if e.errno != errno.ENOENT:
                raise

def apply_patches():
    name = os.path.basename( os.getcwd() )
    for file in glob.glob( os.path.join( patches, name, '*' ) ):
        shutil.copy( file, os.path.basename( file ) )

def get_archive( base ):
    for arctype in ( 'tar.gz', 'tgz', 'zip' ):
        archive = '.'.join( ( base, arctype ) )
        if os.path.exists( archive ):
            return archive
    else:
        raise Exception( "%s(): Couldn't find a suitable archive for %s in %s" % ( sys._getframe().f_code.co_name, os.path.basename( base ), archives ) )

def compress( path, *files ):
    tarcf( path, *files )

def uncompress( path ):
    if path.endswith( '.zip' ):
        unzip( path )
    else:
        tarxf( path )

def unzip( zipf ):
    z = zipfile.ZipFile( zipf )
    try:
        for info in z.infolist():
            name = info.filename
            mode = (info.external_attr >> 16L) & 0777
            # don't extract absolute paths or ones with .. in them
            if name.startswith('/') or '..' in name:
                continue
            if not name:
                continue
            if name.endswith('/'):
                # directory
                pkg_resources.ensure_directory(name)
            else:
                # file
                pkg_resources.ensure_directory(name)
                data = z.read(info.filename)
                f = open(name,'wb')
                try:
                    f.write(data)
                finally:
                    f.close()
                    del data
                try:
                    if not os.path.islink( name ):
                        os.chmod(name,mode)
                except:
                    pass
    finally:
        z.close()

def tarxf( ball ):
    t = tarfile.open( ball, 'r' )
    for fn in t.getnames():
        t.extract( fn )
    t.close()

def tarcf( ball, *files ):
    if ball.endswith( '.gz' ):
        t = tarfile.open( ball, 'w:gz' )
    elif ball.endswith( '.bz2' ):
        t = tarfile.open( ball, 'w:bz2' )
    else:
        t = tarfile.open( ball, 'w' )
    for file in files:
        t.add( file )
    t.close()

def run( cmd, d, txt ):
    p = subprocess.Popen( args = cmd, shell = True, cwd = d )
    r = p.wait()
    if r != 0:
        print '%s(): %s failed' % ( sys._getframe().f_code.co_name, txt )
        sys.exit( 1 )

def unpack_dep( source, prepped, builder, args={} ):
    if prepped is not None and os.path.exists( prepped ):
        print "%s(): Prepared dependency already exists at the following path, remove to force re-prep:" % sys._getframe().f_code.co_name
        print " ", prepped
        uncompress( prepped )
    else:
        print "%s(): Prepared dependency does not exist, preparing now from source:" % sys._getframe().f_code.co_name
        print " ", source
        uncompress( source )
        builder( prepped, args )

def get_solaris_compiler():
    p = subprocess.Popen( '%s -V 2>&1' % get_config_var('CC'), shell = True, stdout = subprocess.PIPE )
    out = p.stdout.read()
    p.wait()
    if 'Sun C' in out:
        return 'cc'
    else:
        return 'gcc'

# get galaxy eggs lib
galaxy_lib = os.path.abspath( os.path.join( os.path.dirname( __file__ ), '..', '..', '..', 'lib' ) )
sys.path.insert( 0, galaxy_lib )
from galaxy import eggs

# get setuptools
try:
    from setuptools import *
    import pkg_resources
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools( download_delay=8, to_dir=os.path.dirname( __file__ ) )
    from setuptools import *
    import pkg_resources

# some constants
root = os.path.abspath( os.path.join( os.path.dirname( __file__ ), '..' ) )
archives = os.path.abspath( os.path.join( root, 'archives' ) )
patches = os.path.abspath( os.path.join( root, 'patches' ) )
platform_noucs = pkg_resources.get_platform().rsplit( '-', 1 )[0]
