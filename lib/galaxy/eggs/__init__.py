"""
Manage Galaxy eggs
"""

import os, sys, shutil, tarfile, zipfile, subprocess, ConfigParser, glob, urllib2
from types import ModuleType

import logging
log = logging.getLogger( __name__ )

import pkg_resources

# we MUST have the top level galaxy dir for automatic egg fetching
# within tools.  i don't know of any way around this. -ndc
galaxy_dir = os.path.abspath( os.path.join( os.path.dirname( __file__ ), "..", "..", ".." ) )

class NewEgg( Exception ):
    pass

class EggNotFetchable( Exception ):
    pass

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
            for doppelganger in self.doppelgangers:
                os.unlink( doppelganger )
                log.debug( "Removed conflicting egg: %s" % doppelganger )
            return True
    def scramble( self ):
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
        for doppelganger in self.doppelgangers:
            os.unlink( doppelganger )
            log.warning( "Removed conflicting egg: %s" % doppelganger )
        return True
    # scramble helper methods
    def get_archive_path( self, url ):
        return os.path.join( Egg.archive_dir, (url.rsplit( '/', 1 ))[1] )
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
        tld = ( z.namelist()[0].split( os.path.sep, 1 ) )[0]
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
        tld = ( t.getnames()[0].split( os.path.sep, 1 ) )[0]
        cur = os.getcwd()
        os.chdir( unpack_path )
        for member in t.getmembers():
            if "ez_setup" not in member.name:
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
        self.no_download = []
        self.platform = { 'peak' : get_platform( platform=True, peak=True ), 'galaxy' : get_platform( platform=True, peak=False ) }
        self.noplatform = { 'peak' : get_platform( platform=False, peak=True ), 'galaxy' : get_platform( platform=False, peak=False ) }
    def parse( self ):
        if self.config.read( Crate.config_file ) == []:
            raise Exception( "unable to read egg config from %s" % Crate.config_file )
        try:
            self.repo = self.config.get( "general", "repository" )
            self.no_download = self.config.get( "general", "no_download" ).split()
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
        ignore.extend( self.no_download )
        try:
            f = urllib2.urlopen( "%s/%s" % ( self.repo, self.platform['galaxy'] ) )
            f.close()
        except urllib2.HTTPError, e:
            if e.code == 404:
                skip_platform = True
                missing = []
        for egg in self.eggs.itervalues():
            if ignore is not None:
                if egg.name in ignore:
                    continue
            if skip_platform and egg.platform['galaxy'] == self.platform['galaxy']:
                missing.append( egg.name )
                continue
            egg.fetch()
        if skip_platform:
            raise PlatformNotSupported( self.platform['galaxy'] )
        return True
    def scramble( self, ignore=None ):
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
            self.hosts = self.dictize_list_of_tuples( self.config.items( "hosts" ) )
            self.groups = self.dictize_list_of_tuples( self.config.items( "groups" ) )
        except ConfigParser.NoSectionError, e:
            raise Exception( "eggs.ini is missing required section: %s" % e )
        self.platforms = self.get_platforms( self.build_on )
        self.noplatforms = self.get_platforms( 'noplatform' )
        Crate.parse( self )
    def dictize_list_of_tuples( self, lot ):
        """
	Makes a list of 2-value tuples into a dict.
        """
        d = {}
        for k, v in lot:
            d[k] = v
        return d
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
    def __init__( self ):
        self.config = ConfigParser.ConfigParser()
        if self.config.read( GalaxyConfig.config_file ) == []:
            raise Exception( "error: unable to read Galaxy config from %s" % GalaxyConfig.config_file )
    # TODO: conditionals should really be handled better than this
    def check_conditional( self, egg_name ):
        if egg_name == "psycopg2":
            try:
                if self.config.get( "app:main", "database_connection" ).startswith( "postgres://" ):
                    return True
                else:
                    return False
            except:
                return False
        elif egg_name == "pysqlite":
            try:
                # database connection is the sqlite alchemy dialect (not really
                # a documented usage in Galaxy, but it would work)
                if self.config.get( "app:main", "database_connection" ).startswith( "sqlite://" ):
                    return True
                else:
                    return False
            # database connection is unset, so sqlite is the default
            except:
                return True
        elif egg_name == "DRMAA_python":
            try:
                runners = self.config.get( "app:main", "start_job_runners" ).split(",")
                if "sge" in runners:
                    return True
                else:
                    return False
            except:
                return False
        elif egg_name == "pbs_python":
            try:
                runners = self.config.get( "app:main", "start_job_runners" ).split(",")
                if "pbs" in runners:
                    return True
                else:
                    return False
            except:
                return False
        elif egg_name == "threadframe":
            try:
                if self.config.get( "app:main", "use_heartbeat" ) == "True":
                    return True
                else:
                    return False
            except:
                return False
        elif egg_name == "guppy":
            try:
                if self.config.get( "app:main", "use_memdump" ) == "True":
                    return True
                else:
                    return False
            except:
                return False
        elif egg_name == "MySQL_python":
            try:
                if self.config.get( "app:main", "database_connection" ).startswith( "mysql://" ):
                    return True
                else:
                    return False
            except:
                return False
        else:
            return True

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
            pkg_resources.working_set.require( pkg )
        else:
            pkg_resources.working_set.require( "%s==%s" % ( name, egg.get_vertag() ) )
        return
    except pkg_resources.VersionConflict, e:
        # there's a conflicting egg on the pythonpath, remove it
        dist = pkg_resources.get_distribution( name )
        working_set = pkg_resources.working_set
        # use the canonical path for comparisons
        location = os.path.realpath( dist.location )
        for entry in working_set.entries:
            if os.path.realpath( entry ) == location:
                working_set.entries.remove( entry )
                break
        else:
            raise   # some path weirdness has prevented us from finding the offender
        del working_set.by_key[dist.key]
        working_set.entry_keys[entry] = []
        sys.path.remove(entry)
        # get
        egg.find()
        if not egg.have:
            if not egg.fetch():
                raise EggNotFetchable( egg.name )
            pkg_resources.working_set.require( "%s==%s" % ( name, egg.get_vertag() ) )
            if dist.project_name in sys.modules:
                try:
                    mod = sys.modules[dist.project_name]
                    reload( mod )
                except:
                    raise NewEgg( "Galaxy downloaded a new egg (%s) but was unable to reload the module it contained.  Please try starting Galaxy again." % egg.name )
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
    require( pkg )

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

pkg_resources.require = require
