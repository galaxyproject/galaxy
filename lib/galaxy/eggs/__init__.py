"""
Manage Galaxy eggs
"""

import os, sys, shutil, tarfile, zipfile, zipimport, subprocess, ConfigParser, glob, urllib2, shutil
from types import ModuleType

import logging
log = logging.getLogger( __name__ )

import pkg_resources

# we MUST have the top level galaxy dir for automatic egg fetching
# within tools.  i don't know of any way around this. -ndc
galaxy_dir = os.path.abspath( os.path.join( os.path.dirname( __file__ ), "..", "..", ".." ) )

class EggNotFetchable( Exception ):
    def __init__( self, eggs ):
        if type( eggs ) in ( list, tuple ):
            self.eggs = eggs
        else:
            self.eggs = [ eggs ]

class PlatformNotSupported( Exception ):
    pass

# TODO: we should really be using exceptions instead of returns for everything

# need the options to remain case sensitive
class CSConfigParser( ConfigParser.SafeConfigParser ):
    def optionxform( self, optionstr ):
        return optionstr

class Egg( object ):
    """
    Contains information about locating, downloading and scrambling eggs.
    """
    archive_dir = os.path.join( galaxy_dir, "scripts", "scramble", "archives" )
    script_dir = os.path.join( galaxy_dir, "scripts", "scramble", "scripts" )
    build_dir = os.path.join( galaxy_dir, "scripts", "scramble", "build" )
    ez_setup = os.path.join( galaxy_dir, "scripts", "scramble", "lib", "ez_setup.py" )
    ez_setup_url = "http://peak.telecommunity.com/dist/ez_setup.py"
    def __init__( self ):
        self.name = None
        self.version = None
        self.tag = None
        self.sources = []
        self.platform = {}
        self.url = None
        self.have = False
        self.path = None
        self.doppelgangers = []
        self.buildpath = None
        self.dir = None
        self.build_host = None
        self.python = sys.executable
    def set_dir( self ):
        if self.build_host is not None:
            self.dir = os.path.join( galaxy_dir, "dist-eggs", self.platform['galaxy'] )
        else:
            self.dir = os.path.join( galaxy_dir, "eggs", self.platform['galaxy'] )
    def get_namever( self ):
        return( "%s-%s" %( self.name, self.version ) )
    def get_namevertag( self ):
        if self.tag is None:
            return( "%s-%s" %( self.name, self.version ) )
        else:
            return( "%s-%s%s" %( self.name, self.version, self.tag ) )
    def get_vertag( self ):
        if self.tag is None:
            return self.version
        else:
            return( "%s%s" %( self.version, self.tag ) )
    def get_filename( self ):
        if self.tag is None:
            return( "%s-%s-%s.egg" %( self.name, self.version, self.platform['peak'] ) )
        else:
            return( "%s-%s%s-%s.egg" %( self.name, self.version, self.tag, self.platform['peak'] ) )
    def find( self ):
        # TODO: should be able to set a search path in eggs.ini
        if self.dir is None:
            self.set_dir()
        self.path = os.path.join( self.dir, self.get_filename() )
        self.doppelgangers = glob.glob( os.path.join( self.dir, "%s-*-%s.egg" % (self.name, self.platform['peak'] ) ) )
        if os.access( self.path, os.F_OK ):
            self.have = True
            self.doppelgangers.remove( self.path )
    def fetch( self ):
        if self.path is None:
            self.find()
        if not self.have:
            if not os.access( os.path.dirname( self.path ), os.F_OK ):
                os.makedirs( os.path.dirname( self.path ) )
            try:
                inf = urllib2.urlopen( self.url )
                otf = open( self.path, 'wb' )
                otf.write( inf.read() )
                inf.close()
                otf.close()
                log.debug( "Fetched %s" % self.url )
            except urllib2.HTTPError, e:
                raise EggNotFetchable( self.name )
                #if e.code == 404:
                #    return False
            self.unpack_if_needed()
            for doppelganger in self.doppelgangers:
                remove_file_or_path( doppelganger )
                log.debug( "Removed conflicting egg: %s" % doppelganger )
            return True
    def unpack_if_needed( self ):
        meta = pkg_resources.EggMetadata( zipimport.zipimporter( self.path ) )    
        if meta.has_metadata( 'not-zip-safe' ):
            unpack_zipfile( self.path, self.path + "-tmp" )
            os.remove( self.path )
            os.rename( self.path + "-tmp", self.path )
    def scramble( self, dist=False ):
        if self.path is None:
            self.find()
        if os.access( self.path, os.F_OK ):
            log.warning( "scramble(): Egg already exists, remove to force rebuild:" )
            log.warning( "  %s" % self.path )
            return True
        self.fetch_source()
        self.unpack_source()
        self.copy_build_script()
        if not os.access( Egg.ez_setup, os.F_OK ):
            if not os.access( os.path.dirname( Egg.ez_setup ), os.F_OK ):
                os.makedirs( os.path.dirname( Egg.ez_setup ) )
            inf = urllib2.urlopen( Egg.ez_setup_url )
            otf = open( Egg.ez_setup, 'wb' )
            otf.write( inf.read() )
            inf.close()
            otf.close()
        shutil.copyfile( Egg.ez_setup, os.path.join( self.buildpath, "ez_setup.py" ) )
        log.warning( "scramble(): Beginning build" )
        # subprocessed to sterilize the env
        if self.build_host is not None:
            cmd = "ssh %s 'cd %s; %s -ES %s'" % ( self.build_host, self.buildpath, self.python, "scramble.py" )
        else:
            cmd = "%s -ES %s" % ( self.python, "scramble.py" )
        p = subprocess.Popen( args = cmd, shell = True, cwd = self.buildpath )
        r = p.wait()
        if r != 0:
            log.error( "scramble(): Egg build failed for %s" % self.get_namevertag() )
            return False
        new_egg = os.path.join( self.buildpath, "dist", os.path.basename( self.path ) )
        if not os.access( os.path.dirname( self.path ), os.F_OK ):
            os.makedirs( os.path.dirname( self.path ) )
        shutil.copyfile( new_egg, self.path )
        log.warning( "scramble(): Copied egg to:" )
        log.warning( "  %s" % self.path )
        if not dist:
            self.unpack_if_needed()
        for doppelganger in self.doppelgangers:
            remove_file_or_path( doppelganger )
            log.warning( "Removed conflicting egg: %s" % doppelganger )
        return True
    # scramble helper methods
    def get_archive_path( self, url ):
        return os.path.join( Egg.archive_dir, (url.rsplit( '/', 1 ))[1] )
    def get_tld( self, names ):
        tld = names[0].split( os.path.sep, 1 )[0]
        for name in names:
            try:
                assert tld == name.split( os.path.sep, 1 )[0]
            except:
                raise Exception( "get_tld(): Archive contains multiple top-level directories!" )
        return tld
    def fetch_source( self ):
        if not os.access( Egg.archive_dir, os.F_OK ):
            os.makedirs( Egg.archive_dir )
        for source_url in self.sources:
            source_path = self.get_archive_path( source_url )
            if os.access( source_path, os.F_OK ):
                log.warning( "fetch_source(): Using existing source, remove to download again:" )
                log.warning( "  %s" % source_path )
                continue
            log.warning( "fetch_source(): Attempting to download" )
            log.warning( "  %s" % source_url )
            inf = urllib2.urlopen( source_url )
            otf = open( source_path, 'wb' )
            otf.write( inf.read() )
            inf.close()
            otf.close()
            log.warning( "fetch_source(): Fetched %s" % source_url )
    def unpack_source( self ):
        unpack_dir = os.path.join( Egg.build_dir, self.platform['galaxy'] )
        if not os.access( unpack_dir, os.F_OK ):
            os.makedirs( unpack_dir )
        self.buildpath = os.path.join( unpack_dir, self.name )
        if os.access( self.buildpath, os.F_OK ):
            log.warning( "Removing old build directory at:" )
            log.warning( "  %s" % self.buildpath )
            shutil.rmtree( self.buildpath )
        source_path = self.get_archive_path( self.sources[0] )
        if tarfile.is_tarfile( source_path ):
            self.unpack = self.unpack_tar
        elif zipfile.is_zipfile( source_path ):
            self.unpack = self.unpack_zip
        else:
            raise Exception( "unpack_source(): Unknown archive file type for %s" % source_path )
        self.unpack( source_path, unpack_dir )
        log.warning( "unpack_source(): Unpacked to:" )
        log.warning( "  %s" % self.buildpath )
    def unpack_zip( self, source_path, unpack_path ):
        z = zipfile.ZipFile( source_path, "r" )
        tld = self.get_tld( z.namelist() )
        cur = os.getcwd()
        os.chdir( unpack_path )
        for fn in z.namelist():
            if "ez_setup" in fn:
                continue
            if not os.access( os.path.dirname( fn ), os.F_OK ):
                os.makedirs( os.path.dirname( fn ) )
            otf = open( fn, "wb" )
            otf.write( z.read( fn ) )
            otf.close()
        z.close()
        os.rename( tld, self.name )
        os.chdir( cur )
    def unpack_tar( self, source_path, unpack_path ):
        t = tarfile.open( source_path, "r" )
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
        peak_platform = get_platform( platform=True, peak=True )
        nopy_platform = ( peak_platform.split( "-", 1 ) )[1]
        just_os = ( nopy_platform.split( "-", 1 ) )[0]
        just_py = ( peak_platform.split( "-", 1 ) )[0]
        # will try:
        #   bx_python-py2.4-solaris-2.11-i86pc.py
        #   bx_python-py2.4-solaris.py
        #   bx_python-solaris-2.11-i86pc.py
        #   bx_python-solaris.py
        #   bx_python-py2.4.py
        #   bx_python.py
        #   generic.py
        build_scripts = [
            os.path.join( Egg.script_dir, "%s-%s.py" % ( self.name, peak_platform ) ),
            os.path.join( Egg.script_dir, "%s-%s-%s.py" % ( self.name, just_py, just_os ) ),
            os.path.join( Egg.script_dir, "%s-%s.py" % ( self.name, nopy_platform ) ),
            os.path.join( Egg.script_dir, "%s-%s.py" % ( self.name, just_os ) ),
            os.path.join( Egg.script_dir, "%s-%s.py" % ( self.name, just_py ) ),
            os.path.join( Egg.script_dir, "%s.py" % self.name ),
            os.path.join( Egg.script_dir, "generic.py" )
        ]
        for build_script in build_scripts:
            try:
                f = open( build_script, "r" )
                f.close()
                log.warning( "scramble(): Using build script %s" % build_script )
                break
            except IOError:
                pass
        shutil.copyfile( build_script, os.path.join( self.buildpath, "scramble.py" ) )
        if self.tag is not None:
            tagfile = open( os.path.join( self.buildpath, ".galaxy_tag" ), "w" )
            print >>tagfile, self.tag
            tagfile.close()

class Crate( object ):
    """
    Reads the eggs.ini file for use with checking, fetching and scrambling eggs.
    """
    config_file = os.path.join( galaxy_dir, "eggs.ini" )
    def __init__( self ):
        self.eggs = {}
        self.config = CSConfigParser()
        self.repo = None
        self.no_auto = []
        self.platform = { 'peak' : get_platform( platform=True, peak=True ), 'galaxy' : get_platform( platform=True, peak=False ) }
        self.noplatform = { 'peak' : get_platform( platform=False, peak=True ), 'galaxy' : get_platform( platform=False, peak=False ) }
    def parse( self ):
        if self.config.read( Crate.config_file ) == []:
            raise Exception( "unable to read egg config from %s" % Crate.config_file )
        try:
            self.repo = self.config.get( "general", "repository" )
            self.no_auto = self.config.get( "general", "no_auto" ).split()
        except ConfigParser.NoSectionError:
            raise Exception( "eggs.ini is missing required section [general]" )
        #except ConfigParser.NoOptionError:
        #    raise Exception( "eggs.ini is missing required [general] option 'repository'" )
        try:
            platform_eggs = self.config.items( "eggs:platform" )
            noplatform_eggs = self.config.items( "eggs:noplatform" )
        except ConfigParser.NoSectionError, e:
            raise Exception( "eggs.ini is missing required section: %s" % e )
        self.parse_egg_section( platform_eggs, self.platform )
        self.parse_egg_section( noplatform_eggs, self.noplatform )
    def parse_egg_section( self, eggs, platform ):
        for name, version in eggs:
            egg = Egg()
            try:
                egg.tag = self.config.get( "tags", name )
            except:
                egg.tag = None
            try:
                egg.sources = self.config.get( "source", name ).split()
            except:
                egg.sources = None
            egg.name = name
            egg.version = version
            egg.platform['galaxy'] = platform['galaxy']
            egg.platform['peak'] = platform['peak']
            egg.url = "%s/%s/%s" %( self.repo, platform['galaxy'], egg.get_filename() )
            self.eggs[name] = egg
    def find( self, ignore=None ):
        missing = []
        for egg in self.eggs.itervalues():
            if ignore is not None:
                if egg.name in ignore:
                    continue
            egg.find()
            if not egg.have:
                missing.append( egg.name )
        if len( missing ):
            return False
        return True
    def fetch( self, ignore=[] ):
        """
        Fetch all eggs in the crate (ignoring any that you want to
        ignore).  If your platform isn't available, it'll attempt to
        download all the noplatform eggs before failing.
        """
        skip_platform = False
        ignore.extend( self.no_auto )
        missing = []
        try:
            f = urllib2.urlopen( "%s/%s" % ( self.repo, self.platform['galaxy'] ) )
            f.close()
        except urllib2.HTTPError, e:
            if e.code == 404:
                skip_platform = True
        for egg in self.eggs.itervalues():
            if ignore is not None:
                if egg.name in ignore:
                    continue
            if skip_platform and egg.platform['galaxy'] == self.platform['galaxy']:
                missing.append( egg.name )
                continue
            try:
                egg.fetch()
            except EggNotFetchable:
                missing.append( egg.name )
        if skip_platform:
            raise PlatformNotSupported( self.platform['galaxy'] )
        if missing:
            raise EggNotFetchable( missing )
        return True
    def scramble( self, ignore=None ):
        # Crate-scrambling the no_auto eggs makes no sense
        ignore.extend( self.no_auto )
        for egg in self.eggs.itervalues():
            if ignore is not None:
                if egg.name in ignore:
                    continue
            if not egg.scramble():
                return False
        return True
    def get_names( self ):
        return self.eggs.keys()
    def get( self, name ):
        if self.eggs.has_key( name ):
            return self.eggs[name]
        else:
            return None
    def get_for_require( self, name ):
        """
        return an egg based on a lowercase name comparo and with _ instead of -.  used by require.
        """
        for key in self.eggs.keys():
            if key.lower() == name.lower().replace( '-', '_' ):
                return self.eggs[key]

class DistCrate( Crate ):
    """
    A subclass of Crate that holds eggs with info on how to build them for distribution.
    """
    dist_config_file = os.path.join( galaxy_dir, "dist-eggs.ini" )
    def __init__( self, build_on="all" ):
        self.eggs = {}
        self.config = CSConfigParser()
        self.repo = None
        self.build_on = build_on
        self.platform = 'platform'
        self.noplatform = 'noplatform'
    def parse( self ):
        if self.config.read( DistCrate.dist_config_file ) == []:
            raise Exception( "unable to read dist egg config from %s" % DistCrate.dist_config_file )
        try:
            self.hosts = dict( self.config.items( "hosts" ) )
            self.groups = dict( self.config.items( "groups" ) )
            self.ignore = dict( self.config.items( "ignore" ) )
        except ConfigParser.NoSectionError, e:
            raise Exception( "eggs.ini is missing required section: %s" % e )
        self.platforms = self.get_platforms( self.build_on )
        self.noplatforms = self.get_platforms( 'noplatform' )
        Crate.parse( self )
    def get_platforms( self, wanted ):
        # find all the members of a group and process them
        if self.groups.has_key( wanted ):
            platforms = []
            for name in self.groups[wanted].split():
                for platform in self.get_platforms( name ):
                    if platform not in platforms:
                        platforms.append( platform )
            return platforms
        elif self.hosts.has_key( wanted ):
            return [ wanted ]
        else:
            raise Exception( "unknown platform: %s" % wanted )
    def parse_egg_section( self, eggs, type ):
        """
        Overrides the base class's method.  Here we use the third arg
        to find out what type of egg we'll be building.
        """
        if type == "platform":
            platforms = self.platforms
        elif type == "noplatform":
            platforms = self.noplatforms
        for name, version in eggs:
            for platform in platforms:
                # can't use the regular methods here because we're not
                # actually ON the target platform
                if type == "platform":
                    gplat = platform
                    pplat = platform.rsplit('-', 1)[0]
                elif type == "noplatform":
                    gplat = "%s-noplatform" % platform.split('-', 1)[0]
                    pplat = platform.split('-', 1)[0]
                if name in self.ignore and gplat in self.ignore[name].split():
                    continue
                egg = Egg()
                try:
                    egg.tag = self.config.get( "tags", name )
                except:
                    egg.tag = None
                try:
                    egg.sources = self.config.get( "source", name ).split()
                except:
                    egg.sources = None
                egg.name = name
                egg.version = version
                egg.platform['galaxy'] = gplat
                egg.platform['peak'] = pplat
                egg.url = "%s/%s/%s" %( self.repo, gplat, egg.get_filename() )
                egg.build_host, egg.python = self.hosts[platform].split()
                if not self.eggs.has_key( name ):
                    self.eggs[name] = [ egg ]
                else:
                    self.eggs[name].append( egg )

class GalaxyConfig:
    config_file = os.path.join( galaxy_dir, "universe_wsgi.ini" )
    always_conditional = ( 'GeneTrack', )
    def __init__( self ):
        self.config = ConfigParser.ConfigParser()
        if self.config.read( GalaxyConfig.config_file ) == []:
            raise Exception( "error: unable to read Galaxy config from %s" % GalaxyConfig.config_file )
    # TODO: conditionals should really be handled better than this
    def check_conditional( self, egg_name ):
        if egg_name == "pysqlite":
            # SQLite is different since it can be specified in two config vars and defaults to True
            try:
                return self.config.get( "app:main", "database_connection" ).startswith( "sqlite://" )
            except:
                return True
        else:
            try:
                return { "psycopg2":        lambda: self.config.get( "app:main", "database_connection" ).startswith( "postgres://" ),
                         "MySQL_python":    lambda: self.config.get( "app:main", "database_connection" ).startswith( "mysql://" ),
                         "DRMAA_python":    lambda: "sge" in self.config.get( "app:main", "start_job_runners" ).split(","),
                         "pbs_python":      lambda: "pbs" in self.config.get( "app:main", "start_job_runners" ).split(","),
                         "threadframe":     lambda: self.config.get( "app:main", "use_heartbeat" ),
                         "guppy":           lambda: self.config.get( "app:main", "use_memdump" ),
                         "GeneTrack":       lambda: sys.version_info[:2] >= ( 2, 5 ),
                       }.get( egg_name, lambda: True )()
            except:
                return False

def require( pkg ):
    # add the egg dirs to sys.path if they're not already there
    for platform in [ get_platform(), get_platform( platform=True ) ]:
        path = os.path.join( galaxy_dir, "eggs", platform )
        if path not in sys.path:
            new_path = [ path ]
            new_path.extend( sys.path )
            sys.path = new_path
            pkg_resources.working_set.add_entry(path)
    name = pkg_resources.Requirement.parse( pkg ).project_name
    c = Crate()
    c.parse()
    egg = c.get_for_require( name )
    try:
        if egg is None:
            return pkg_resources.working_set.require( pkg )
        else:
            return pkg_resources.working_set.require( "%s==%s" % ( name, egg.get_vertag() ) )
    except pkg_resources.VersionConflict, e:
        # there's a conflicting egg on the pythonpath, remove it
        dist = e.args[0]
        working_set = pkg_resources.working_set
        # use the canonical path for comparisons
        location = os.path.realpath( dist.location )
        for entry in working_set.entries:
            if os.path.realpath( entry ) == location:
                working_set.entries.remove( entry )
                break
        else:
            location = None
        del working_set.by_key[dist.key]
        working_set.entry_keys[entry] = []
        sys.path.remove(entry)
        r = require( pkg )
        if location is not None and not location.endswith( '.egg' ):
            working_set.entries.append( location ) # re-add to the set if it's a dir.
        return r
    except pkg_resources.DistributionNotFound, e:
        # the initial require itself is the first dep, but it can have
        # multiple deps, which will be fetched by the require below.
        dep = pkg_resources.Requirement.parse( str( e ) ).project_name
        egg = c.get_for_require( dep )
        if egg is None:
            # we don't have it and we can't get it
            raise
        egg.find()
        if not egg.have:
            if not egg.fetch():
                raise EggNotFetchable( egg.name )
        return require( pkg )

# convenience stuff
def get_ucs():
    if sys.maxunicode > 65535:
        return "ucs4"
    else:
        return "ucs2"

def get_py():
    return "py%s" % sys.version[:3]

def get_noplatform():
    return "%s-noplatform" % get_py()

def get_platform( platform=False, peak=False ):
    if platform:
        if peak:
            return "%s-%s" % ( get_py(), pkg_resources.get_platform() )
        else:
            return "%s-%s-%s" % ( get_py(), pkg_resources.get_platform(), get_ucs() )
    else:
        if peak:
            return get_py()
        else:
            return "%s-noplatform" % get_py()

def unpack_zipfile( filename, extract_dir):
    z = zipfile.ZipFile(filename)
    try:
        for info in z.infolist():
            name = info.filename
            # don't extract absolute paths or ones with .. in them
            if name.startswith('/') or '..' in name:
                continue
            target = os.path.join(extract_dir, *name.split('/'))
            if not target:
                continue
            if name.endswith('/'):
                # directory
                pkg_resources.ensure_directory(target)
            else:
                # file
                pkg_resources.ensure_directory(target)
                data = z.read(info.filename)
                f = open(target,'wb')
                try:
                    f.write(data)
                finally:
                    f.close()
                    del data
    finally:
        z.close()

def remove_file_or_path( f ):
    if os.path.isdir( f ):
        shutil.rmtree( f )
    else:
        os.remove( f )

pkg_resources.require = require
