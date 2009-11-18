"""
Galaxy root package -- this is a namespace package.
"""

# Starting somewhere in 2.5.x, Python on Mac became broken - despite being fat,
# the machine portion of the platform is not set to 'fat'.
#
# For more, see:
#
# http://bugs.python.org/setuptools/issue19
#
import os, sys
from distutils.sysconfig import get_config_vars

if sys.version_info[:2] == ( 2, 5 ) and \
        ( ( os.uname()[-1] in ( 'i386', 'ppc' ) and sys.platform == 'darwin' and os.path.abspath( sys.prefix ).startswith( '/System' ) ) or \
          ( sys.platform == 'darwin' and get_config_vars().get('UNIVERSALSDK', '').strip() ) ):
    # Has to be before anything imports pkg_resources
    def _get_platform_monkeypatch():
        plat = distutils.util._get_platform()
        if plat.startswith( 'macosx-' ):
            plat = 'macosx-10.3-fat'
        return plat
    import distutils.util
    try:
        assert distutils.util._get_platform
    except:
        distutils.util._get_platform = distutils.util.get_platform
        distutils.util.get_platform = _get_platform_monkeypatch

__import__( "pkg_resources" ).declare_namespace( __name__ )
