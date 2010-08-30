#!/usr/bin/env python

# Configure stdout logging

import os, sys, logging, glob, zipfile, shutil

log = logging.getLogger()
log.setLevel( 10 )
log.addHandler( logging.StreamHandler( sys.stdout ) )

# Fake pkg_resources

import re

macosVersionString = re.compile(r"macosx-(\d+)\.(\d+)-(.*)")
darwinVersionString = re.compile(r"darwin-(\d+)\.(\d+)\.(\d+)-(.*)")
solarisVersionString = re.compile(r"solaris-(\d)\.(\d+)-(.*)")

def compatible_platforms(provided,required):
    """Can code for the `provided` platform run on the `required` platform?

    Returns true if either platform is ``None``, or the platforms are equal.

    XXX Needs compatibility checks for Linux and other unixy OSes.
    """
    if provided is None or required is None or provided==required:
        return True     # easy case

    # Mac OS X special cases
    reqMac = macosVersionString.match(required)
    if reqMac:
        provMac = macosVersionString.match(provided)

        # is this a Mac package?
        if not provMac:
            # this is backwards compatibility for packages built before
            # setuptools 0.6. All packages built after this point will
            # use the new macosx designation.
            provDarwin = darwinVersionString.match(provided)
            if provDarwin:
                dversion = int(provDarwin.group(1))
                macosversion = "%s.%s" % (reqMac.group(1), reqMac.group(2))
                if dversion == 7 and macosversion >= "10.3" or \
                    dversion == 8 and macosversion >= "10.4":

                    #import warnings
                    #warnings.warn("Mac eggs should be rebuilt to "
                    #    "use the macosx designation instead of darwin.",
                    #    category=DeprecationWarning)
                    return True
            return False    # egg isn't macosx or legacy darwin

        # are they the same major version and machine type?
        if provMac.group(1) != reqMac.group(1) or \
            provMac.group(3) != reqMac.group(3):
            return False



        # is the required OS major update >= the provided one?
        if int(provMac.group(2)) > int(reqMac.group(2)):
            return False

        return True

    # Solaris' special cases
    reqSol = solarisVersionString.match(required)
    if reqSol:
        provSol = solarisVersionString.match(provided)
        if not provSol:
            return False
        if provSol.group(1) != reqSol.group(1) or \
            provSol.group(3) != reqSol.group(3):
            return False
        if int(provSol.group(2)) > int(reqSol.group(2)):
            return False
        return True

    # XXX Linux and other platforms' special cases should go here
    return False

EGG_NAME = re.compile(
    r"(?P<name>[^-]+)"
    r"( -(?P<ver>[^-]+) (-py(?P<pyver>[^-]+) (-(?P<plat>.+))? )? )?",
    re.VERBOSE | re.IGNORECASE
).match

class Distribution( object ):
    def __init__( self, egg_name, project_name, version, py_version, platform ):
        self._egg_name = egg_name
        self.project_name = project_name
        if project_name is not None:
            self.project_name = project_name.replace( '-', '_' )
        self.version = version
        if version is not None:
            self.version = version.replace( '-', '_' )
        self.py_version = py_version
        self.platform = platform
        self.location = os.path.join( tmpd, egg_name ) + '.egg'
    def egg_name( self ):
        return self._egg_name
    @classmethod
    def from_filename( cls, basename ):
        project_name, version, py_version, platform = [None]*4
        basename, ext = os.path.splitext(basename)
        if ext.lower() == '.egg':
            match = EGG_NAME( basename )
            if match:
                project_name, version, py_version, platform = match.group( 'name','ver','pyver','plat' )
        return cls( basename, project_name, version, py_version, platform )

class pkg_resources( object ):
    pass

pkg_resources.Distribution = Distribution

# Fake galaxy.eggs

env = None
def get_env():
    return None

import urllib, urllib2, HTMLParser
class URLRetriever( urllib.FancyURLopener ):
    def http_error_default( *args ):
        urllib.URLopener.http_error_default( *args )

class Egg( object ):
    def __init__( self, distribution ):
        self.url = url + '/' + distribution.project_name.replace( '-', '_' )
        self.dir = tmpd
        self.distribution = distribution
    def set_distribution( self ):
        pass
    def unpack_if_needed( self ):
        pass
    def remove_doppelgangers( self ):
        pass
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
                        compatible_platforms( tmp_dist.platform, self.distribution.platform ):
                    return file
            return None
        if self.url is None:
            return None
        alternative = None
        try:
            url = self.url + '/' + self.distribution.egg_name() + '.egg'
            URLRetriever().retrieve( url, self.distribution.location )
            log.debug( "Fetched %s" % url )
        except IOError, e:
            if e[1] == 404 and self.distribution.platform != py:
                alternative = find_alternative()
                if alternative is None:
                    return None
            else:
                return None
        if alternative is not None:
            try:
                url = '/'.join( ( self.url, alternative ) )
                URLRetriever().retrieve( url, os.path.join( self.dir, alternative ) )
                log.debug( "Fetched %s" % url )
            except IOError, e:
                return None
            self.platform = alternative.split( '-', 2 )[-1].rsplit( '.egg', 1 )[0]
            self.set_distribution()
        self.unpack_if_needed()
        self.remove_doppelgangers()
        global env
        env = get_env() # reset the global Environment object now that we've obtained a new egg
        return self.distribution

def create_zip():
    fname = 'galaxy_eggs-%s.zip' % platform
    z = zipfile.ZipFile( fname, 'w', zipfile.ZIP_STORED )
    for egg in glob.glob( os.path.join( tmpd, '*.egg' ) ):
        z.write( egg, 'eggs/' + os.path.basename( egg ) )
    z.close()
    print 'Egg package is in %s' % fname
    print "To install the eggs, please copy this file to your Galaxy installation's root"
    print "directory and unpack with:"
    print "  unzip %s" % fname

def clean():
    shutil.rmtree( tmpd )

import tempfile
tmpd = tempfile.mkdtemp()

failures = []

# Automatically generated egg definitions follow

