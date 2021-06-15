"""
Utility functions for bi-directional Python version compatibility.  Python 2.5
introduced hashlib which replaced sha in Python 2.4 and previous versions.
"""

import hashlib
import hmac
import logging

from . import smart_str


log = logging.getLogger(__name__)

BLOCK_SIZE = 1024 * 1024

sha1 = hashlib.sha1
sha256 = hashlib.sha256
sha512 = hashlib.sha512
sha = sha1
md5 = hashlib.md5

HASH_NAME_MAP = {
    "MD5": md5,
    "SHA-1": sha1,
    "SHA-256": sha256,
    "SHA-512": sha512,
}
HASH_NAMES = list(HASH_NAME_MAP.keys())


def memory_bound_hexdigest(hash_func=None, hash_func_name=None, path=None, file=None):
    if hash_func is None:
        assert hash_func_name is not None
        hash_func = HASH_NAME_MAP[hash_func_name]

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
    except OSError:
        # This may happen if path has been deleted
        return None


def new_secure_hash(text_type):
    """
    Returns the hexdigest of the sha1 hash of the argument `text_type`.
    """
    assert text_type is not None
    return sha1(smart_str(text_type)).hexdigest()


def hmac_new(key, value):
    return hmac.new(smart_str(key), smart_str(value), sha).hexdigest()


def is_hashable(value):
    try:
        hash(value)
    except Exception:
        return False
    return True


__all__ = ('md5', 'hashlib', 'sha1', 'sha', 'new_secure_hash', 'hmac_new', 'is_hashable')
