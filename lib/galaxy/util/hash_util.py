"""
Utility functions for bi-directional Python version compatibility.  Python 2.5
introduced hashlib which replaced sha in Python 2.4 and previous versions.
"""
from __future__ import absolute_import

import hashlib
import hmac
import logging

from . import smart_str


log = logging.getLogger(__name__)

BLOCK_SIZE = 1024 * 1024

sha1 = hashlib.sha1
sha256 = hashlib.sha256
sha = sha1
md5 = hashlib.md5


def memory_bound_hexdigest(hash_func, path=None, file=None):
    hasher = hash_func()
    if file is None:
        assert path is not None
        file = open(path, "rb")
    else:
        assert path is None, "Cannot specify path and path keyword arguments."

    try:
        for block in iter(lambda: file.read(BLOCK_SIZE), b''):
            hasher.update(block)
        return hasher.hexdigest()
    finally:
        file.close()


def md5_hash_file(path):
    """
    Return a md5 hashdigest for a file or None if path could not be read.
    """
    hasher = hashlib.md5()
    try:
        with open(path, 'rb') as afile:
            buf = afile.read()
            hasher.update(buf)
            return hasher.hexdigest()
    except IOError:
        # This may happen if path has been deleted
        return None


def new_secure_hash(text_type=None):
    """
    Returns either a sha1 hash object (if called with no arguments), or a
    hexdigest of the sha1 hash of the argument `text_type`.
    """
    if text_type:
        return sha1(smart_str(text_type)).hexdigest()
    else:
        return sha1()


def hmac_new(key, value):
    return hmac.new(key, value, sha).hexdigest()


def is_hashable(value):
    try:
        hash(value)
    except Exception:
        return False
    return True


__all__ = ('md5', 'hashlib', 'sha1', 'sha', 'new_secure_hash', 'hmac_new', 'is_hashable')
