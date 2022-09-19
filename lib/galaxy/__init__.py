"""
Galaxy root package -- this is a namespace package.
"""

from pkgutil import extend_path

__path__ = extend_path(__path__, __name__)  # type: ignore[has-type]
