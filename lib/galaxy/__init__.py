"""
Galaxy root package -- this is a namespace package.
"""

from pkgutil import extend_path
__path__ = extend_path(__path__, __name__)


# compat: BadZipFile introduced in Python 2.7
import zipfile
if not hasattr(zipfile, 'BadZipFile'):
    zipfile.BadZipFile = zipfile.error
