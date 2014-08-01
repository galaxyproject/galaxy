"""
Manage Galaxy eggs
"""

import os, sys, shutil, glob, urllib, urllib2, ConfigParser, HTMLParser, zipimport, zipfile

import logging
log = logging.getLogger( __name__ )
log.addHandler( logging.NullHandler() )

import pkg_resources

galaxy_dir = os.path.abspath( os.path.join( os.path.dirname( __file__ ), '..', '..', '..' ) )
eggs_dir = os.environ.get( 'GALAXY_EGGS_PATH', os.path.join( galaxy_dir, 'eggs' ) )
py = 'py%s' % sys.version[:3]

class EggNotFetchable( Exception ):
    def __init__( self, eggs ):
        if type( eggs ) in ( list, tuple ):
            self.eggs = eggs
        else:
            self.eggs = [ eggs ]
    def __str__( self ):
        return ' '.join( self.eggs )

# need the options to remain case sensitive
class CaseSensitiveConfigParser( ConfigParser.SafeConfigParser ):
    def optionxform( self, optionstr ):
        return optionstr

# so we can actually detect failures
class URLRetriever( urllib.FancyURLopener ):
    def http_error_default( *args ):
        urllib.URLopener.http_error_default( *args )

class Egg( object ):
    """
    Contains information about locating and downloading eggs.
    """
    def __init__( self, name=None, version=None, tag=None, url=None, platform=None, crate=None ):
        self.name = name
        self.version = version
        self.tag = tag
        self.url = url
        self.platform = platform
        self.crate = crate
        self.distribution = None
        self.dir = None
        self.removed_location = None
        if self.name is not None and self.version is not None:
            self.set_distribution()
    def set_dir( self ):
        global eggs_dir
        self.dir = eggs_dir
        if not os.path.exists( self.dir ):
            os.makedirs( self.dir )
    def set_distribution( self ):
        """
        Stores a pkg_resources Distribution object for reference later
        """
        if self.dir is None:
            self.set_dir()
        tag = self.tag or ''
        self.distribution = pkg_resources.Distribution.from_filename(
                os.path.join( self.dir, '-'.join( ( self.name, self.version + tag, self.platform ) ) + '.egg' ) )
    @property
    def path( self ):
        """
        Return the path of the egg, if it exists, or None
        """
        if env[self.distribution.project_name]:
            return env[self.distribution.project_name][0].location
        return None
    def fetch( self, requirement ):
        """
        fetch() serves as the install method to pkg_resources.working_set.resolve()
        """
        def find_alternative():
            """
            Some platforms (e.g. Solaris) support eggs compiled on older platforms
            """
            class LinkParser( HTMLParser.HTMLParser ):
                """
                Finds links in what should be an Apache-style directory index
                """
                def __init__( self ):
                    HTMLParser.HTMLParser.__init__( self )
                    self.links = []
                def handle_starttag( self, tag, attrs ):
                    if tag == 'a' and 'href' in dict( attrs ):
                        self.links.append( dict( attrs )['href'] )
            parser = LinkParser()
            try:
                parser.feed( urllib2.urlopen( self.url + '/' ).read() )
            except urllib2.HTTPError, e:
                if e.code == 404:
                    return None
            parser.close()
            for link in parser.links:
                file = urllib.unquote( link ).rsplit( '/', 1 )[-1]
                tmp_dist = pkg_resources.Distribution.from_filename( file )
                if tmp_dist.platform is not None and \
                        self.distribution.project_name == tmp_dist.project_name and \
                        self.distribution.version == tmp_dist.version and \
                        self.distribution.py_version == tmp_dist.py_version and \
                        pkg_resources.compatible_platforms( tmp_dist.platform, pkg_resources.get_platform() ):
                    return file
            return None
        def _fetch():
            if self.url is None:
                return False
            alternative = None
            try:
                url = self.url + '/' + self.distribution.egg_name() + '.egg'
                URLRetriever().retrieve( url, self.distribution.location )
                log.debug( "Fetched %s" % url )
            except IOError, e:
                if e[1] == 404 and self.distribution.platform != py:
                    alternative = find_alternative()
                    if alternative is None:
                        return False
                else:
                    return False
            if alternative is not None:
                try:
                    url = '/'.join( ( self.url, alternative ) )
                    URLRetriever().retrieve( url, os.path.join( self.dir, alternative ) )
                    log.debug( "Fetched %s" % url )
                except IOError, e:
                    return False
                self.platform = alternative.split( '-', 2 )[-1].rsplit( '.egg', 1 )[0]
                self.set_distribution()
            self.unpack_if_needed()
            self.remove_doppelgangers()
            return True
        # If being called from a version conflict, that code has removed a
        # directory from sys.path.  That directory could be Python's main lib
        # directory (e.g. in the case of wsgiref under 2.6).  Temporarily put
        # it back during the execution of this code.
        if self.removed_location:
            sys.path.append( self.removed_location )
        try:
            assert _fetch()
            rval = self.distribution
        except:
            rval = None
        if self.removed_location:
            sys.path.remove( self.removed_location )
        if rval is not None:
            global env
            env = get_env() # reset the global Environment object now that we've obtained a new egg
        return rval
    def unpack_if_needed( self ):
        meta = pkg_resources.EggMetadata( zipimport.zipimporter( self.distribution.location ) )
        if meta.has_metadata( 'not-zip-safe' ):
            unpack_zipfile( self.distribution.location, self.distribution.location + "-tmp" )
            os.remove( self.distribution.location )
            os.rename( self.distribution.location + "-tmp", self.distribution.location )
    def remove_doppelgangers( self ):
        doppelgangers = glob.glob( os.path.join( self.dir, "%s-*-%s.egg" % ( self.name, self.platform ) ) )
        if self.distribution.location in doppelgangers:
            doppelgangers.remove( self.distribution.location )
        for doppelganger in doppelgangers:
            remove_file_or_path( doppelganger )
            log.debug( "Removed conflicting egg: %s" % doppelganger )
    def resolve( self ):
        try:
            rval = []
            # resolve this egg and its dependencies
            dists = pkg_resources.working_set.resolve( ( self.distribution.as_requirement(), ), env, self.fetch )
            for dist in dists:
                # if any of the resolved dependencies should be managed eggs but are being pulled from the wrong path, fix them
                if dist.project_name in self.crate.all_names and not os.path.realpath( dist.location ).startswith( os.path.realpath( self.dir ) ):
                    # TODO: like eggs.require(), this breaks requirement versioning
                    subdists = self.version_conflict( dist, dist.as_requirement() )
                    if type( subdists ) == list:
                        rval.extend( subdists )
                    else:
                        rval.append( subdists )
                else:
                    rval.append( dist )
            return rval
        except pkg_resources.DistributionNotFound, e:
            # If this statement is true, it means we do have the requested egg,
            # just not one (or more) of its deps.
            if e.args[0].project_name != self.distribution.project_name:
                log.warning( "Warning: %s (a dependent egg of %s) cannot be fetched" % ( e.args[0].project_name, self.distribution.project_name ) )
                return ( self.distribution, )
            else:
                raise EggNotFetchable( self )
        except pkg_resources.VersionConflict, e:
            if e.args[1].key != e.args[0].key:
                log.error( "One of Galaxy's managed eggs depends on something which is missing, this is almost certainly a bug in the egg distribution." )
                log.error( 'Dependency "%s" requires "%s"' % ( e.args[0].project_name, str( e.args[1] ) ) )
                raise
            # there's a conflicting egg on the path, remove it
            return self.version_conflict( e.args[0], e.args[1] )
    def version_conflict( self, conflict_dist, conflict_req ):
        # since this conflict may be for a dependent egg, find the correct egg from the crate
        if conflict_dist.project_name == self.distribution.project_name:
            egg = self
            dist = egg.distribution
        elif conflict_dist.project_name in self.crate.all_names:
            egg = self.crate[conflict_dist.project_name]
            dist = egg.distribution
        else:
            # should not happen, but just in case
            egg = None
            dist = conflict_dist
        # use the canonical path to locate and remove the conflict from the working set
        location = os.path.realpath( conflict_dist.location )
        for entry in pkg_resources.working_set.entries:
            if os.path.realpath( entry ) == location:
                pkg_resources.working_set.entries.remove( entry )
                break
        else:
            location = entry = None
        del pkg_resources.working_set.by_key[conflict_dist.key]
        # remove the conflict from sys.path
        if entry is not None:
            pkg_resources.working_set.entry_keys[entry] = []
            if entry in sys.path:
                sys.path.remove(entry)
        # if the conflict is a dependent egg, fetch that specific egg
        if egg:
            # Store the removed path so the fetch method can use it
            egg.removed_location = location
            r = pkg_resources.working_set.resolve( ( dist.as_requirement(), ), env, egg.fetch )
            egg.removed_location = None
        else:
            r = pkg_resources.working_set.resolve( ( dist.as_requirement(), ), env )
        # re-add the path if it's a non-egg dir, in case more deps live there
        if location is not None and not location.endswith( '.egg' ):
            pkg_resources.working_set.entries.append( location )
            sys.path.append( location )
        return r
    def require( self ):
        try:
            dists = self.resolve()
            for dist in dists:
                if dist.location not in pkg_resources.working_set.entries:
                    pkg_resources.working_set.add( dist )
            return dists
        except:
            raise

class Crate( object ):
    """
    Reads the eggs.ini file for use with checking and fetching.
    """
    config_file = os.path.join( galaxy_dir, 'eggs.ini' )
    def __init__( self, galaxy_config_file, platform=None ):
        self.eggs = {}
        self.config = CaseSensitiveConfigParser()
        self.repo = None
        self.no_auto = []
        self.platform = platform
        self.py_platform = None
        if platform is not None:
            self.py_platform = platform.split( '-' )[0]
        self.galaxy_config = GalaxyConfig( galaxy_config_file )
        self.parse()
    def parse( self ):
        self.config.read( Crate.config_file )
        self.repo = self.config.get( 'general', 'repository' )
        self.no_auto = self.config.get( 'general', 'no_auto' ).split()
        self.parse_egg_section( self.config.items( 'eggs:platform' ), self.config.items( 'tags' ), True )
        self.parse_egg_section( self.config.items( 'eggs:noplatform' ), self.config.items( 'tags' ) )
    def parse_egg_section( self, eggs, tags, full_platform=False, egg_class=Egg ):
        for name, version in eggs:
            tag = dict( tags ).get( name, '' )
            url = '/'.join( ( self.repo, name ) )
            if full_platform:
                platform = self.platform or '-'.join( ( py, pkg_resources.get_platform() ) )
            else:
                platform = self.py_platform or py
            egg = egg_class( name=name, version=version, tag=tag, url=url, platform=platform, crate=self )
            self.eggs[name] = egg
    @property
    def config_missing( self ):
        """
        Return true if any eggs are missing, conditional on options set in the
        Galaxy config file.
        """
        for egg in self.config_eggs:
            if not egg.path:
                return True
        return False
    @property
    def all_missing( self ):
        """
        Return true if any eggs in the eggs config file are missing.
        """
        for egg in self.all_eggs:
            if not os.path.exists( egg.distribution.location ):
                return True
        return False
    @property
    def config_names( self ):
        """
        Return a list of names of all eggs in the crate that are needed based
        on the options set in the Galaxy config file.
        """
        return [ egg.name for egg in self.config_eggs ]
    @property
    def all_names( self ):
        """
        Return a list of names of all eggs in the crate.
        """
        return [ egg.name for egg in self.all_eggs ]
    @property
    def config_eggs( self ):
        """
        Return a list of all eggs in the crate that are needed based on the
        options set in the Galaxy config file.
        """
        return [ egg for egg in self.eggs.values() if self.galaxy_config.check_conditional( egg.name ) ]
    @property
    def all_eggs( self ):
        """
        Return a list of all eggs in the crate.
        """
        rval = []
        for egg in self.eggs.values():
            if egg.name in self.galaxy_config.always_conditional and not self.galaxy_config.check_conditional( egg.name ):
                continue
            rval.append( egg )
        return rval
    def __getitem__( self, name ):
        """
        Return a specific egg.
        """
        name = name.replace( '-', '_' )
        return self.eggs[name]
    def resolve( self, all=False ):
        """
        Try to resolve (e.g. fetch) all eggs in the crate.
        """
        if all:
            eggs = self.all_eggs
        else:
            eggs = self.config_eggs
        eggs = filter( lambda x: x.name not in self.no_auto, eggs )
        missing = []
        for egg in eggs:
            try:
                egg.resolve()
            except EggNotFetchable:
                missing.append( egg )
        if missing:
            raise EggNotFetchable( missing )

class GalaxyConfig( object ):
    always_conditional = ( 'pysam', 'ctypes', 'python_daemon' )
    def __init__( self, config_file ):
        if config_file is None:
            self.config = None
        else:
            self.config = ConfigParser.ConfigParser()
            if self.config.read( config_file ) == []:
                raise Exception( "error: unable to read Galaxy config from %s" % config_file )
    def check_conditional( self, egg_name ):
        def check_pysam():
            # can't build pysam on solaris < 10
            plat = pkg_resources.get_platform().split( '-' )
            if plat[0] == 'solaris':
                minor = plat[1].split('.')[1]
                if int( minor ) < 10:
                    return False
            return True
        # If we're using require() we may not have a Galaxy config file, but if
        # we're using require(), we don't care about conditionals.
        if self.config is None:
            return True
        if egg_name == "pysqlite":
            # SQLite is different since it can be specified in two config vars and defaults to True
            try:
                return self.config.get( "app:main", "database_connection" ).startswith( "sqlite://" )
            except:
                return True
        else:
            try:
                return { "psycopg2":        lambda: self.config.get( "app:main", "database_connection" ).startswith( "postgres" ),
                         "MySQL_python":    lambda: self.config.get( "app:main", "database_connection" ).startswith( "mysql://" ),
                         "DRMAA_python":    lambda: "sge" in self.config.get( "app:main", "start_job_runners" ).split(","),
                         "drmaa":           lambda: "drmaa" in self.config.get( "app:main", "start_job_runners" ).split(","),
                         "pbs_python":      lambda: "pbs" in self.config.get( "app:main", "start_job_runners" ).split(","),
                         "threadframe":     lambda: self.config.get( "app:main", "use_heartbeat" ),
                         "guppy":           lambda: self.config.get( "app:main", "use_memdump" ),
                         "python_openid":   lambda: self.config.get( "app:main", "enable_openid" ),
                         "python_daemon":   lambda: sys.version_info[:2] >= ( 2, 5 ),
                         "pysam":           lambda: check_pysam(),
                         "PyRods":          lambda: self.config.get( "app:main", "object_store" ) == "irods"
                       }.get( egg_name, lambda: True )()
            except:
                return False

def get_env():
    env = pkg_resources.Environment( search_path='', platform=pkg_resources.get_platform() )
    for dist in pkg_resources.find_distributions( eggs_dir, False ):
        env.add( dist )
    return env
env = get_env()

def require( req_str ):
    c = Crate( None )
    req = pkg_resources.Requirement.parse( req_str )
    # TODO: This breaks egg version requirements.  Not currently a problem, but
    # it could become one.
    try:
        return c[req.project_name].require()
    except KeyError:
        # not a galaxy-owned dependency
        return pkg_resources.working_set.require( req_str )
    except EggNotFetchable, e:
        raise EggNotFetchable( str( [ egg.name for egg in e.eggs ] ) )
pkg_resources.require = require

def unpack_zipfile( filename, extract_dir, ignores=[] ):
    z = zipfile.ZipFile(filename)
    try:
        for info in z.infolist():
            name = info.filename
            perm = (info.external_attr >> 16L) & 0777
            # don't extract absolute paths or ones with .. in them
            if name.startswith('/') or '..' in name:
                continue
            target = os.path.join(extract_dir, *name.split('/'))
            if not target:
                continue
            for ignore in ignores:
                if ignore in name:
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
                try:
                    if not os.path.islink():
                        os.chmod(target, mode)
                except:
                    pass
    finally:
        z.close()

def remove_file_or_path( f ):
    if os.path.isdir( f ):
        shutil.rmtree( f )
    else:
        os.remove( f )
