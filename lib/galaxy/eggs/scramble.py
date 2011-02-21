"""
Manage Galaxy eggs
"""

import os, sys, shutil, tempfile, subprocess, urlparse, urllib
from __init__ import Egg, Crate, URLRetriever, galaxy_dir, py, unpack_zipfile, EggNotFetchable
from distutils.sysconfig import get_config_var

import tarfile, zipfile, zlib
arctypes = ( 'tar.gz', 'tgz', 'zip' )

import logging
log = logging.getLogger( __name__ )
log.addHandler( logging.NullHandler() )

import pkg_resources

class ScrambleFailure( Exception ):
    def __init__( self, eggs, msg=None ):
        if type( eggs ) in ( list, tuple ):
            self.eggs = eggs
        else:
            self.eggs = [ eggs ]
        self.msg = msg
    def __str__( self ):
        return self.msg or ' '.join( self.eggs )

class ScrambleEgg( Egg ):
    """
    Contains information about scrambling eggs.
    """
    scramble_dir = os.path.join( galaxy_dir, 'scripts', 'scramble' )
    archive_dir = os.path.join( scramble_dir, 'archives' )
    script_dir = os.path.join( scramble_dir, 'scripts' )
    build_dir = os.path.join( scramble_dir, 'build' )
    ez_setup = os.path.join( scramble_dir, 'lib', 'ez_setup.py' )
    ez_setup_url = 'http://peak.telecommunity.com/dist/ez_setup.py'
    def __init__( self, *args, **kwargs ):
        Egg.__init__( self, *args, **kwargs )
        self.sources = []
        self.dependencies = []
        self.buildpath = None
        self.source_path = None
        self.py = py
        self.build_host = None
        self.python = sys.executable
    def scramble( self ):
        if self.path:
            log.warning( "%s(): Egg already exists, remove to force rebuild:" % sys._getframe().f_code.co_name )
            log.warning( "  %s" % self.path )
            return
        self.fetch_source()
        self.unpack_source()
        self.copy_build_script()
        if not os.path.exists( ScrambleEgg.ez_setup ):
            URLRetriever().retrieve( ScrambleEgg.ez_setup_url, ScrambleEgg.ez_setup )
        self.run_scramble_script()
        new_egg = os.path.join( self.buildpath, 'dist', os.path.basename( self.distribution.location ) )
        if not os.path.exists( new_egg ):
            raise ScrambleFailure( self, "%s(): Egg build for %s did not appear to fail, but no egg found to copy from expected path:\n  %s" % ( sys._getframe().f_code.co_name, self.name, new_egg ) )
        shutil.copyfile( new_egg, self.distribution.location )
        log.warning( "%s(): Copied egg to:" % sys._getframe().f_code.co_name )
        log.warning( "  %s" % self.distribution.location )
        self.unpack_if_needed()
        self.remove_doppelgangers()
    # scramble helper methods
    def get_tld( self, names ):
        tld = names[0].split( os.path.sep, 1 )[0]
        for name in names:
            try:
                assert tld == name.split( os.path.sep, 1 )[0]
            except:
                raise Exception( "%s(): Archive contains multiple top-level directories!" % sys._getframe().f_code.co_name )
        return tld
    def fetch_one( self, urls ):
        """
        Fetches the first available archive out of a list.
        """
        for url in urls:
            file = os.path.join( ScrambleEgg.archive_dir, ( urllib.unquote( url ).rsplit( '/', 1 ) )[-1] )
            if os.path.exists( file ):
                log.warning( "%s(): Using existing source, remove to download again:" % sys._getframe().f_code.co_name )
                log.warning( "  %s" % file )
                return file
        # if we don't have one, get one
        for url in urls:
            file = os.path.join( ScrambleEgg.archive_dir, ( urllib.unquote( url ).rsplit( '/', 1 ) )[-1] )
            try:
                log.debug( "%s(): Trying to fetch:" % sys._getframe().f_code.co_name )
                log.debug( "  %s" % url )
                URLRetriever().retrieve( url, file + '.download' )
                shutil.move( file + '.download', file )
                log.debug( "%s(): Fetched to:" % sys._getframe().f_code.co_name )
                log.debug( "  %s" % file )
                return file
            except IOError, e:
                if e[1] != 404:
                    raise
        else:
            return None
    def fetch_source( self ):
        """
        Get egg (and dependent) source
        """
        if not os.path.exists( ScrambleEgg.archive_dir ):
            os.makedirs( ScrambleEgg.archive_dir )
        urls = []
        url_base = self.url + '/' + '-'.join( ( self.name, self.version ) )
        urls.extend( map( lambda x: '.'.join( ( url_base, x ) ), arctypes ) )
        if self.tag:
            urls.extend( map( lambda x: '.'.join( ( url_base + self.tag, x ) ), arctypes ) )
        self.source_path = self.fetch_one( urls )
        if self.source_path is None:
            raise Exception( "%s(): Couldn't find a suitable source archive for %s %s from %s" % ( sys._getframe().f_code.co_name, self.name, self.version, self.url ) )
        for url in self.sources:
            if not urlparse.urlparse( url )[0]:
                url = self.url + '/' + url.lstrip( '/' )
            urls = [ url ]
            urls.extend( map( lambda x: '.'.join( ( url, x ) ), arctypes ) ) # allows leaving off the extension and we'll try to find one
            file = self.fetch_one( urls )
            if file is None:
                raise Exception( "%s(): Couldn't fetch extra source for %s, check path in %s.  URL(s) attempted output above." % ( sys._getframe().f_code.co_name, self.name, Crate.config_file, ) )
    def unpack_source( self ):
        unpack_dir = os.path.join( ScrambleEgg.build_dir, self.platform )
        if not os.path.exists( unpack_dir ):
            os.makedirs( unpack_dir )
        self.buildpath = os.path.join( unpack_dir, self.name )
        if os.path.exists( self.buildpath ):
            log.warning( "%s(): Removing old build directory at:" % sys._getframe().f_code.co_name )
            log.warning( "  %s" % self.buildpath )
            shutil.rmtree( self.buildpath )
        if tarfile.is_tarfile( self.source_path ):
            self.unpack_tar()
        elif zipfile.is_zipfile( self.source_path ):
            self.unpack_zip()
        else:
            raise Exception( "%s(): Unknown archive file type for %s" % ( sys._getframe().f_code.co_name, source_path ) )
        log.warning( "%s(): Unpacked to:" % sys._getframe().f_code.co_name )
        log.warning( "  %s" % self.buildpath )
    def unpack_zip( self ):
        unpack_path = os.path.dirname( self.buildpath )
        tld = self.get_tld( zipfile.ZipFile( self.source_path, 'r' ).namelist() )
        unpack_zipfile( self.source_path, unpack_path, ( 'ez_setup', ) )
        os.rename( os.path.join( unpack_path, tld ), self.buildpath )
    def unpack_tar( self ):
        unpack_path = os.path.dirname( self.buildpath )
        t = tarfile.open( self.source_path, "r" )
        members = filter( lambda x: "ez_setup" not in x.name and "pax_global_header" != x.name, t.getmembers() )
        tld = self.get_tld( [ x.name for x in members ] )
        cur = os.getcwd()
        os.chdir( unpack_path )
        for member in members:
            t.extract( member )
        t.close()
        os.rename( tld, self.name )
        os.chdir( cur )
    def copy_build_script( self ):
        # will try:
        #   bx_python-py2.4-solaris-2.11-i86pc.py
        #   bx_python-py2.4-solaris.py
        #   bx_python-solaris-2.11-i86pc.py
        #   bx_python-solaris.py
        #   bx_python-py2.4.py
        #   bx_python.py
        #   generic.py
        platform = self.platform.replace( '-ucs2', '' ).replace( '-ucs4', '' ) # ucs is unimportant here
        build_scripts = (
            "%s-%s.py" % ( self.name, platform ),
            "%s-%s.py" % ( self.name, '-'.join( platform.split( '-' )[:2] ) ),
            "%s-%s.py" % ( self.name, '-'.join( platform.split( '-' )[1:] ) ),
            "%s-%s.py" % ( self.name, platform.split( '-' )[:2][-1] ),
            "%s-%s.py" % ( self.name, platform.split( '-' )[0] ),
            "%s.py" % self.name,
            "generic.py" )
        for build_script in build_scripts:
            build_script = os.path.join( ScrambleEgg.script_dir, build_script )
            if os.path.exists( build_script ):
                log.warning( "%s(): Using build script %s" % ( sys._getframe().f_code.co_name, build_script ) )
                break
        shutil.copyfile( build_script, os.path.join( self.buildpath, "scramble.py" ) )
        verfile = open( os.path.join( self.buildpath, ".galaxy_ver" ), "w" )
        verfile.write( self.version + '\n' )
        verfile.close()
        if self.tag is not None:
            tagfile = open( os.path.join( self.buildpath, ".galaxy_tag" ), "w" )
            tagfile.write( self.tag + '\n' )
            tagfile.close()
        if self.dependencies:
            depfile = open( os.path.join( self.buildpath, ".galaxy_deps" ), "w" )
            for dependency in self.dependencies:
                depfile.write( dependency + '\n' )
            depfile.close()
    def run_scramble_script( self ):
        log.warning( "%s(): Beginning build" % sys._getframe().f_code.co_name )
        # subprocessed to sterilize the env
        cmd = "%s %s" % ( self.python, "scramble.py" )
        log.debug( '%s(): Executing in %s:' % ( sys._getframe().f_code.co_name, self.buildpath ) )
        log.debug( '  %s' % cmd )
        p = subprocess.Popen( args = cmd, shell = True, cwd = self.buildpath )
        r = p.wait()
        if r != 0:
            if sys.platform == 'sunos5' and get_config_var('CC').endswith('pycc') and not os.environ.get( 'PYCC_CC', None ):
                log.error( "%s(): Your python interpreter was compiled with Sun's pycc" % sys._getframe().f_code.co_name )
                log.error( "  pseudo-compiler.  You may need to set PYCC_CC and PYCC_CXX in your" )
                log.error( "  environment if your compiler is in a non-standard location." )
            raise ScrambleFailure( self, "%s(): Egg build failed for %s %s" % ( sys._getframe().f_code.co_name, self.name, self.version ) )

class ScrambleCrate( Crate ):
    """
    Reads the eggs.ini file for use with scrambling eggs.
    """
    def parse( self ):
        Crate.parse( self )
        # get dependency sources
        for egg in self.eggs.values():
            try:
                egg.sources = self.config.get( "source", egg.name ).split()
            except:
                egg.sources = []
            try:
                egg.dependencies = self.config.get( "dependencies", egg.name ).split()
            except:
                egg.dependencies = []
    def parse_egg_section( self, *args, **kwargs ):
        kwargs['egg_class'] = ScrambleEgg
        Crate.parse_egg_section( self, *args, **kwargs )
    def scramble( self, all=False ):
        if all:
            eggs = self.all_eggs
        else:
            eggs = self.config_eggs
        eggs = filter( lambda x: x.name not in self.no_auto, eggs )
        failed = []
        for egg in eggs:
            try:
                egg.scramble()
            except Exception, e:
                failed.append( egg )
                last_exc = e
        if failed:
            if len( failed ) == 1:
                raise last_exc # only 1 failure out of the crate, be more informative
            else:
                raise ScrambleFailure( failed )
