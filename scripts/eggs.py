"""
Manage and build Galaxy eggs
"""

import os, sys, shutil, tarfile, zipfile, subprocess
import ConfigParser
import glob

# convenience stuff
def get_platform():
    return pkg_resources.get_platform()

def get_ucs():
    if sys.maxunicode > 65535:
        return "ucs4"
    else:
        return "ucs2"

def get_py():
    return "py%s" % sys.version[:3]

def get_noplatform():
    return "%s-noplatform" % get_py()

def get_full_platform():
    return "%s-%s-%s" % ( get_py(), get_platform(), get_ucs() )

# need pkg_resources
here = os.path.abspath( os.path.dirname( sys.argv[0] ) )
galaxy_lib_dir = os.path.abspath( os.path.join( here, "..", "lib" ) )
dist_eggs_dir = os.path.abspath( os.path.join( here, "..", "dist-eggs" ) )
galaxy_eggs_dir = os.path.abspath( os.path.join( here, "..", "eggs" ) )
if os.environ.has_key( "GALAXY_EGGS_DIR" ):
    scramble_eggs_dir = os.environ[ "GALAXY_EGGS_DIR" ]
else:
    scramble_eggs_dir = os.path.abspath( os.path.join( here, "..", "eggs" ) )
egg_config_file = os.path.abspath( os.path.join( here, "..", "eggs.ini" ) )
galaxy_config_file = os.path.abspath( os.path.join( here, "..", "universe_wsgi.ini" ) )
#sys.path.append( lib_dir )
#sys.path.append( os.path.join( galaxy_eggs_dir, get_noplatform() ) )

scramble_dir = os.path.join( here, "scramble" )
archive_dir = os.path.join( scramble_dir, "archives" )
lib_dir = os.path.join( scramble_dir, "lib" )

sys.path.append( lib_dir )
sys.path.append( galaxy_lib_dir )

import pkg_resources

pkg_resources.require( "twill" )
import twill.commands as tc
import twill.errors as te

tc.config( key = "use_tidy", value = False )

# so it won't hang indefinitely
import socket
socket.setdefaulttimeout(60)
import urllib2

class Egg:
    def __init__( self ):
        self.name = None
        self.version = None
        self.url = None
        self.rev = None
        self.tag = None
        self.path = None
        self.src_archive = None
        self.version_tag = None

    def unpack_zip( self, dir ):
        z = zipfile.ZipFile( self.src_archive, "r" )
        for orig_fn in z.namelist():
            fn = ( orig_fn.split( os.path.sep, 1 ) )[1]
            abs_fn = os.path.join( dir, fn )
            if not os.access( os.path.dirname( abs_fn ), os.F_OK ):
                os.makedirs( os.path.dirname( abs_fn ) )
            if os.path.basename( abs_fn ) == "ez_setup.py":
                continue
            otf = open( abs_fn, "wb" )
            otf.write( z.read( orig_fn ) )
            otf.close()
        z.close()

    def unpack_tar( self, dir ):
        t = tarfile.open( self.src_archive, "r" )
        for orig_fn in t.getnames():
            fn = ( orig_fn.split( os.path.sep, 1 ) )[1]
            abs_fn = os.path.join( dir, fn )
            # the top dir will now be an empty string
            if fn == "":
                continue
            if os.path.basename( abs_fn ) == "ez_setup.py":
                continue
            if fn.endswith( os.path.sep ):
                if not os.access( os.path.dirname( abs_fn ), os.F_OK ):
                    os.makedirs( abs_fn )
            else:
                # apparently a tar can contain the dirs or not contain the dirs?
                if not os.access( os.path.dirname( abs_fn ), os.F_OK ):
                    os.makedirs( os.path.dirname( abs_fn ) )
                inf = t.extractfile( orig_fn )
                otf = open( abs_fn, "wb" )
                otf.write( inf.read() )
                otf.close()
        t.close()

    def fetch_source( self ):
        if not os.access( archive_dir, os.F_OK ):
            os.makedirs( archive_dir )
        if os.access( self.src_archive, os.F_OK ):
            print "fetch_source(): Using existing module source, remove to download again:"
            print " ", self.src_archive
            return
        if self.rev is None:
            print "fetch_source(): Attempting to download"
            print " ", self.url
            try:
                tc.go( self.url )
                tc.code( 200 )
                tc.save_html( self.src_archive )
            except te.TwillAssertionError, e:
                print "fetch_source(): Unable to load:"
                print " ", self.url
                sys.exit( 1 )
            except urllib2.URLError, e:
                print "fetch_source(): Connection timed out while trying to contact:"
                print " ", self.url
                sys.exit( 1 )

    def unpack_source( self, dir ):
        try:
            if tarfile.is_tarfile( self.src_archive ):
                self.unpack = self.unpack_tar
            elif zipfile.is_zipfile( self.src_archive ):
                self.unpack = self.unpack_zip
            else:
                print "unpack_source(): Unknown archive file type:"
                print " ", self.src_archive
                sys.exit( 1 )
        except IOError:
            print "unpack_source(): Unable to open source archive, did you call fetch_source() first?"
            sys.exit( 1 )
        self.unpack( dir )
        print "unpack_source(): Unpacked to:"
        print " ", dir

# need the options to remain case sensitive
class CSConfigParser( ConfigParser.SafeConfigParser ):
    def optionxform( self, optionstr ):
        return optionstr

class ConfigEggs:
    def __init__( self ):
        self.eggs = []
        self.config = CSConfigParser()
        self.repo = None
        self.build_hosts = {}
        self.pythons = {}
        self.groups = {}
        if self.config.read( egg_config_file ) == []:
            print "error: unable to read egg config from", egg_config_file
            sys.exit( 1 )
        try:
            self.repo = self.config.get( "general", "repository" )
        except ConfigParser.NoSectionError:
            print "error: eggs.ini is missing required section [general]"
            sys.exit( 1 )
        except ConfigParser.NoOptionError:
            print "error: eggs.ini is missing required [general] option 'repository'"
            sys.exit( 1 )
        try:
            eggs = self.config.options( "eggs" )
        except ConfigParser.NoSectionError:
            print "error: eggs.ini has no [eggs] section"
            sys.exit( 1 )
        for egg in eggs:
            egg_params = self.config.get( "eggs", egg ).split()
            ok = self.check_required_params( egg_params )
            if not ok:
                print "warning: syntax error in eggs.ini for egg '%s' (see above), ignoring" % egg
                continue
            this_egg = Egg()
            this_egg.name = egg
            this_egg.version = egg_params[0]
            this_egg.url = egg_params[1]
            # HACK: if the download url uses http get args, this may not work
            if this_egg.url.endswith( '.tar.bz2' ):
                ext = ".tbz2"
            elif this_egg.url.endswith( '.tar.gz' ):
                ext = ".tgz"
            else:
                ext = ( os.path.splitext( this_egg.url ) )[1]
            this_egg.src_archive = os.path.join( archive_dir, "%s-%s%s" %( this_egg.name, this_egg.version, ext ) )
            # tags are optional
            try:
                this_egg.tag = self.config.get( "tags", egg )
                this_egg.version_tag = this_egg.version + this_egg.tag
            except:
                this_egg.version_tag = this_egg.version
            # svn eggs only
            if len( egg_params ) == 3:
                this_egg.rev = egg_params[2]
                this_egg.version_tag += "_r%s" %this_egg.rev
            self.eggs.append( this_egg )
        try:
            build_platforms = self.config.options( "hosts" )
        except ConfigParser.NoSectionError:
            build_platforms = []
        for plat in build_platforms:
            [ host, py ] = self.config.get( "hosts", plat ).split()
            self.build_hosts[plat] = host
            self.pythons[plat] = py
        try:
            groups = self.config.options( "groups" )
        except ConfigParser.NoSectionError:
            groups = []
        for group in groups:
            plats = self.config.get( "groups", group ).split()
            self.groups[group] = plats
    def check_required_params( self, params ):
        if len( params ) == 0:
            print "error: missing required 'version' parameter"
            return False
        elif len( params ) == 1:
            print "error: missing required 'url' parameter"
            return False
        return True
    def get_eggs( self ):
        return tuple( self.eggs )
    def get_egg( self, egg_name ):
        for egg in self.eggs:
            if egg.name == egg_name:
                return egg
        return None
    def get_build_host( self, plat ):
        if self.build_hosts.has_key( plat ):
            return self.build_hosts[plat]
        else:
            return None
    def get_python( self, plat ):
        if self.pythons.has_key( plat ):
            return self.pythons[plat]
        else:
            return None
    def get_platforms( self, plat ):
        if self.groups.has_key( plat ):
            return tuple( self.groups[plat] )
        else:
            return None

class GalaxyEggs:
    def __init__( self ):
        self.dir = galaxy_eggs_dir
        self.eggs = []
        plat_dir = os.path.join( self.dir, get_full_platform() )
        noplat_dir = os.path.join( self.dir, get_noplatform() )
        for egg in glob.glob( os.path.join( noplat_dir, "*.egg" ) ) + glob.glob( os.path.join( plat_dir, "*.egg" ) ):
            filename = ( os.path.split( egg ) )[1]
            name_split = filename.split("-")
            this_egg = Egg()
            this_egg.name = name_split[0]
            this_egg.version = name_split[1]
            self.eggs.append( this_egg )
    def get_eggs( self ):
        return tuple( self.eggs )
    def find_egg( self, name, version ):
        wrong_version = False
        for egg in self.eggs:
            if egg.name == name:
                if egg.version == version:
                    #print "Found exact match: %s-%s" %( name, version )
                    return True
                else:
                    print "Found egg, but version differs:"
                    print "  want: %s-%s" %( name, version )
                    print "  have: %s-%s" %( egg.name, egg.version )
                    wrong_version = True
        # this won't be reached if a wrong version was found, but a correct
        # version was also eventually found
        if wrong_version:
            return False
        else:
            print "Egg not found: %s" % name
            return False

class GalaxyConfig:
    # technically python_lzo is conditional, but we have no way of knowing
    # whether or not you need it
    def __init__( self ):
        self.config = ConfigParser.ConfigParser()
        if self.config.read( galaxy_config_file ) == []:
            print "error: unable to read Galaxy config from", galaxy_config_file
            sys.exit( 1 )
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

def fetch_eggs( repo, eggs ):

    # our platform names are slightly different than peak's
    galaxy_platform_to_peak_platform = {
        get_noplatform()    : get_py(),
        get_full_platform() : "%s-%s" %( get_py(), get_platform() )
    }
    # try to download from the noplatform url first
    platforms = [ get_noplatform(), get_full_platform() ]

    for platform in platforms:
        url = "%s/%s" %( repo, platform )
        egg_dir = os.path.join( galaxy_eggs_dir, platform )
        if not os.path.exists( egg_dir ):
            try:
                os.makedirs( egg_dir )
            except:
                print "Unable to create egg directory:"
                print " ", egg_dir
                sys.exit( 1 )
        try:
            tc.go( url )
            tc.code( 200 )
        except te.TwillAssertionError, e:
            if tc.get_browser().get_code() == 404:
                print "WARNING: Pre-built eggs are unavailable for %s" % platform
                continue
            else:
                print "ERROR: Unable to load:"
                print " ", url
                sys.exit( 1 )
        except urllib2.URLError, e:
            print "ERROR: Connection timed out while trying to contact repository:"
            print " ", url
            sys.exit( 1 )
        for egg in eggs:
            # the egg filename doesn't include the ucs
            egg_filename = "%s-%s-%s.egg" %( egg.name, egg.version_tag, galaxy_platform_to_peak_platform[platform] )
            egg_url = "%s/%s" %( url, egg_filename )
            egg_path = os.path.join( egg_dir, egg_filename )
            try:
                tc.go( egg_url )
                tc.code( 200 )
            except te.TwillAssertionError, e:
                # 404 is okay, each egg is going to come up 404 for one or the other platforms
                browser = tc.get_browser()
                #if tc.get_browser().get_code() == 404:
                if browser.get_code() == 404:
                    continue
                else:
                    print "WARNING: Unable to load:"
                    print " ", egg_url
                    sys.exit( 1 )
            except urllib2.URLError, e:
                print "ERROR: Connection timed out while trying to download:"
                print " ", egg_url
                sys.exit( 1 )
            # remove any other versions before writing the new one
            for conflicting_egg in glob.glob( os.path.join( egg_dir, "%s-*.egg" %egg.name ) ):
                try:
                    print "Removing conflicting egg:", conflicting_egg
                    os.unlink( conflicting_egg )
                except:
                    print "Unable to remove:", conflicting_egg
                    sys.exit( 1 )
            try:
                tc.save_html( egg_path )
            except:
                print "ERROR: Unable to write to:"
                print " ", egg_path
                sys.exit( 1 )
            egg.path = egg_path
    # any failed eggs will have a None egg.path
    ret = []
    for egg in eggs:
        if egg.path is None:
            print "Failed to download %s-%s" %( egg.name, egg.version_tag )
            ret.append( egg.name )
    return ret

def get_missing_eggs( ceggs, geggs, gconfig ):
    missing_eggs = []
    for egg in ceggs.get_eggs():
        if gconfig == "all":
            if not geggs.find_egg( egg.name, egg.version_tag ):
                missing_eggs.append( egg )
        elif gconfig.check_conditional( egg.name ):
            if not geggs.find_egg( egg.name, egg.version_tag ):
                missing_eggs.append( egg )
        #else:
        #    print "Optional egg '%s' not needed by Galaxy config, ignoring" % egg.name
    return missing_eggs

def scramble( egg_name, platform ):

    from ez_setup import use_setuptools
    use_setuptools( download_delay=8, to_dir=lib_dir )

    config_eggs = ConfigEggs()
    egg = config_eggs.get_egg( egg_name )
    if egg is None:
        print "Egg not found in eggs.ini:", egg_name
        sys.exit( 1 )

    # here's where we fork if we're building multiple eggs
    if platform == "default":
        eggs_dir = scramble_eggs_dir
        platform = get_full_platform()
    #elif platform == "dist":
    #    eggs_dir = dist_eggs_dir
    #    platform = get_full_platform()
    else:
        platforms = config_eggs.get_platforms( platform )
        if platforms is None:
            platforms = [ platform ]
        for platform in platforms:
            host = config_eggs.get_build_host( platform )
            python = config_eggs.get_python( platform )
            if host is not None and python is not None:
                cmd = "ssh %s 'GALAXY_EGGS_DIR=%s %s %s/scramble.py %s'" %( host, dist_eggs_dir, python, here, egg_name )
                print "scramble(): Executing:"
                print " ", cmd
                p = subprocess.Popen( args = cmd, shell = True )
                r = p.wait()
                if r != 0:
                    print "scramble(): SSH to %s failed." %host
            else:
                print "scramble(): Platform not found or syntax error for: %s"% platform
        sys.exit( 0 )

    noucs_platform = ( platform.rsplit( "-", 1 ) )[0]
    nopy_platform = ( noucs_platform.split( "-", 1 ) )[1]
    just_os = ( nopy_platform.split( "-", 1 ) )[0]
    just_py = ( noucs_platform.split( "-", 1 ) )[0]

    dirs = [
        os.path.join( eggs_dir, "%s-noplatform" %just_py, "%s-%s-%s.egg" %( egg.name, egg.version_tag, just_py ) ),
        os.path.join( eggs_dir, platform, "%s-%s-%s.egg" %( egg.name, egg.version_tag, noucs_platform ) )
    ]
    for dir in dirs:
        if os.access( dir, os.F_OK ):
            print "scramble(): Egg already exists, to force building, please remove the old one:"
            print " ", dir
            return

    build_scripts_dir = os.path.join( scramble_dir, "scripts" )
    # will try:
    #   bx_python-py2.4-solaris-2.11-i86pc.py
    #   bx_python-py2.4-solaris.py
    #   bx_python-solaris-2.11-i86pc.py
    #   bx_python-solaris.py
    #   bx_python-py2.4.py
    #   bx_python.py
    #   generic.py
    build_scripts = [
        os.path.join( build_scripts_dir, "%s-%s.py" %( egg_name, noucs_platform ) ),
        os.path.join( build_scripts_dir, "%s-%s-%s.py" %( egg_name, just_py, just_os ) ),
        os.path.join( build_scripts_dir, "%s-%s.py" %( egg_name, nopy_platform ) ),
        os.path.join( build_scripts_dir, "%s-%s.py" %( egg_name, just_os ) ),
        os.path.join( build_scripts_dir, "%s-%s.py" %( egg_name, just_py ) ),
        os.path.join( build_scripts_dir, "%s.py" % egg_name ),
        os.path.join( build_scripts_dir, "generic.py" )
    ]
    for build_script in build_scripts:
        try:
            #print "trying", build_script
            f = open( build_script, "r" )
            f.close()
            print "scramble(): Using build script %s" %build_script
            break
        except IOError:
            pass
    else:
        print "scramble(): Failed to find a suitable build script for %s.  Is the scripts/scramble/ directory intact?" %egg_name
        sys.exit( 1 )
    build_dir = os.path.join( scramble_dir, "build", platform, egg_name )
    copied_build_script = os.path.join( build_dir, "scramble_it.py" )
    if os.access( build_dir, os.F_OK ):
        print "scramble(): Removing old build directory at:"
        print " ", build_dir
        shutil.rmtree( build_dir )
    os.makedirs( build_dir )
    egg.fetch_source()
    egg.unpack_source( build_dir )
    shutil.copyfile( build_script, copied_build_script )
    #os.chdir( build_dir )
    #sys.path.append( build_dir )
    #import galaxy_build_egg
    print "scramble(): Beginning build"
    #galaxy_build_egg.build( egg.tag )
    #execfile( "galaxy_build_egg.py", globals(), { "tag" : egg.tag } )
    #execfile( "galaxy_build_egg.py", {}, { "tag" : egg.tag } )
    # we put the tag in a file so you don't have to know it to call scramble_it.py yourself
    if egg.tag is not None:
        tagfile = open( os.path.join( build_dir, ".galaxy_tag" ), "w" )
        print >>tagfile, egg.tag
        tagfile.close()
    # subprocessed to sterilize the env
    cmd = "%s %s" %( sys.executable, os.path.join( build_dir, "scramble_it.py" ) )
    p = subprocess.Popen( args = cmd, shell = True, cwd = os.getcwd() )
    r = p.wait()
    if r != 0:
        print "scramble(): Egg build failed for %s-%s" %( egg.name, egg.version_tag )
        #print "scramble(): The source can be found here:"
        #print " ", build_dir
        #print "scramble(): Building was attempted with this command:"
        #print " ", cmd
        sys.exit( 1 )

    if os.access( os.path.join( build_dir, "dist", "%s-%s-%s.egg" %( egg.name, egg.version_tag, just_py ) ), os.F_OK ):
        new_egg_dir = os.path.join( eggs_dir, "%s-noplatform" %just_py )
        new_egg_name = "%s-%s-%s.egg" %( egg.name, egg.version_tag, just_py )
    elif os.access( os.path.join( build_dir, "dist", "%s-%s-%s.egg" %( egg.name, egg.version_tag, noucs_platform ) ), os.F_OK ):
        new_egg_dir = os.path.join( eggs_dir, platform )
        new_egg_name = "%s-%s-%s.egg" %( egg.name, egg.version_tag, noucs_platform )
    else:
        print "scramble(): Egg build failed for %s-%s" %( egg.name, egg.version_tag )
        print "scramble(): Found neither in build's dist/ dir:"
        print "  %s-%s-%s.egg" %( egg.name, egg.version_tag, just_py )
        print "  %s-%s-%s.egg" %( egg.name, egg.version_tag, noucs_platform )
        sys.exit( 1 )
    if not os.access( new_egg_dir, os.F_OK ):
        os.makedirs( new_egg_dir )
    shutil.copyfile( os.path.join( build_dir, "dist", new_egg_name ), os.path.join( new_egg_dir, new_egg_name ) )
    print "scramble(): Copied egg %s to egg directory:" %new_egg_name
    print " ", new_egg_dir
