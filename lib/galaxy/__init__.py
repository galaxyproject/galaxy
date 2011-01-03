"""
Galaxy root package -- this is a namespace package.
"""

__import__( "pkg_resources" ).declare_namespace( __name__ )

import os, sys, re
from distutils.sysconfig import get_config_var, get_config_vars

import pkg_resources

# patch get_platform() for better ABI recognition
def _get_build_platform():
    plat = pkg_resources._get_build_platform()
    if sys.version_info[:2] == ( 2, 5 ) and \
        ( ( os.uname()[-1] in ( 'x86_64', 'i386', 'ppc' ) and sys.platform == 'darwin' and os.path.abspath( sys.prefix ).startswith( '/System' ) ) or \
          ( sys.platform == 'darwin' and get_config_vars().get('UNIVERSALSDK', '').strip() ) ):
        plat = 'macosx-10.3-fat'
    if sys.platform == "sunos5" and not (plat.endswith('_32') or plat.endswith('_64')):
        if sys.maxint > 2**31:
            plat += '_64'
        else:
            plat += '_32'
    if sys.platform == "linux2" and sys.maxint < 2**31 and plat.endswith( '-x86_64' ):
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

# patch compatible_platforms() to allow for Solaris binary compatibility
solarisVersionString = re.compile(r"solaris-(\d)\.(\d+)-(.*)")
def _compatible_platforms(provided,required):
    # this is a bit kludgey since we need to know a bit about what happened in
    # the original method
    if provided is None or required is None or provided==required:
        return True     # easy case
    reqMac = pkg_resources.macosVersionString.match(required)
    if reqMac:
        return pkg_resources._compatible_platforms(provided,required)
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
    return False
try:
    assert pkg_resources._compatible_platforms
except:
    pkg_resources._compatible_platforms = pkg_resources.compatible_platforms
    pkg_resources.compatible_platforms = _compatible_platforms

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

# patch to add the NullHandler class to logging
if sys.version_info[:2] < ( 2, 7 ):
    import logging
    class NullHandler( logging.Handler ):
        def emit( self, record ):
            pass
    logging.NullHandler = NullHandler
