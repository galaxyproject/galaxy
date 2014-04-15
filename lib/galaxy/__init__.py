"""
Galaxy root package -- this is a namespace package.
"""

__import__( "pkg_resources" ).declare_namespace( __name__ )

import re
import os
import sys
import platform

import pkg_resources

# patch get_platform() for better ABI recognition
def _get_build_platform():
    plat = pkg_resources._get_build_platform()
    if sys.platform == 'darwin':
        # Assert OS X version is new enough
        current_minor_ver = int( platform.mac_ver()[0].split( '.' )[1] )
        assert current_minor_ver >= 6, 'Galaxy is not compatible with Mac OS X < 10.6 (your version is %s)' % platform.mac_ver()[0]
        # Python build target may be even older, but this will prevent it from
        # fetching our 10.6+ eggs, so fix if necessary (newer versions will be
        # fine)
        plat_split = plat.split( '-' )
        build_minor_ver = int( plat_split[1].split( '.' )[1] )
        if build_minor_ver < 6:
            plat_split[1] = '10.6'
        # Our intel (dual arch) eggs will work fine on single-arch builds
        if plat_split[-1] in ( 'i386', 'x86_64' ):
            plat_split[-1] = 'intel'
        # Ditto universal (if you're not on PPC)
        if plat_split[-1] == 'universal' and platform.processor() != 'powerpc':
            plat_split[-1] = 'intel'
        plat = '-'.join( plat_split )
    elif sys.platform == "linux2" and sys.maxint < 2**31 and plat.endswith( '-x86_64' ):
        # 32 bit Python on 64 bit Linux
        plat = plat.replace( '-x86_64', '-i686' )
    if not (plat.endswith('-ucs2') or plat.endswith('-ucs4')):
        if sys.maxunicode > 2**16:
            plat += '-ucs4'
        else:
            plat += '-ucs2'
    return plat
try:
    assert pkg_resources._get_build_platform
except:
    pkg_resources._get_build_platform = pkg_resources.get_build_platform
    pkg_resources.get_build_platform = _get_build_platform
    pkg_resources.get_platform = _get_build_platform

# patch to insert eggs at the beginning of sys.path instead of at the end
def _insert_on(self, path, loc = None):
    """Insert self.location in path before its nearest parent directory"""

    loc = loc or self.location
    if not loc:
        return

    nloc = pkg_resources._normalize_cached(loc)
    npath= [(p and pkg_resources._normalize_cached(p) or p) for p in path]

    if path is sys.path:
        self.check_version_conflict()
    path.insert(0, loc)

    # remove dups
    while 1:
        try:
            np = npath.index(nloc, 1)
        except ValueError:
            break
        else:
            del npath[np], path[np]

    return
try:
    assert pkg_resources.Distribution._insert_on
except:
    pkg_resources.Distribution._insert_on = pkg_resources.Distribution.insert_on
    pkg_resources.Distribution.insert_on = _insert_on

# compat: BadZipFile introduced in Python 2.7
import zipfile
if not hasattr( zipfile, 'BadZipFile' ):
    zipfile.BadZipFile = zipfile.error

# compat: patch to add the NullHandler class to logging
import logging
if not hasattr( logging, 'NullHandler' ):
    class NullHandler( logging.Handler ):
        def emit( self, record ):
            pass
    logging.NullHandler = NullHandler

import galaxy.eggs
