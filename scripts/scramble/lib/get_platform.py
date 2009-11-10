"""
Monkeypatch get_platform since it's broken on OS X versions of Python 2.5
"""
import os, sys
from distutils.sysconfig import get_config_vars
if sys.platform == 'darwin' and get_config_vars().get('UNIVERSALSDK', '').strip():
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
