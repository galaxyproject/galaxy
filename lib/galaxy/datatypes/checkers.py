"""Module proxies :mod:`galaxy.util.checkers` for backward compatibility.

External datatypes may make use of these functions.
"""
from galaxy.util.checkers import (
    check_binary,
    check_bz2,
    check_gzip,
    check_html,
    check_image,
    check_zip,
    is_bz2,
    is_gzip,
)

__all__ = (
    'check_binary',
    'check_bz2',
    'check_gzip',
    'check_html',
    'check_image',
    'check_zip',
    'is_gzip',
    'is_bz2',
)
