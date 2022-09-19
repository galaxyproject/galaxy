"""
Utility functions for bi-directional Python version compatibility.  Python 2.5
introduced hashlib which replaced sha in Python 2.4 and previous versions.
"""

import hashlib
import hmac
import logging
import os
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Union,
)

from . import smart_str

log = logging.getLogger(__name__)

BLOCK_SIZE = 1024 * 1024

HashFunctionT = Callable[[], "hashlib._Hash"]

sha1 = hashlib.sha1
sha256 = hashlib.sha256
sha512 = hashlib.sha512
sha = sha1
md5 = hashlib.md5


class HashFunctionNameEnum(str, Enum):
    """Particular pieces of information that can be requested for a dataset."""

    md5 = "MD5"
    sha1 = "SHA-1"
    sha256 = "SHA-256"
    sha512 = "SHA-512"


HASH_NAME_MAP: Dict[HashFunctionNameEnum, HashFunctionT] = {
    HashFunctionNameEnum.md5: md5,
    HashFunctionNameEnum.sha1: sha1,
    HashFunctionNameEnum.sha256: sha256,
    HashFunctionNameEnum.sha512: sha512,
}
HASH_NAMES: List[HashFunctionNameEnum] = list(HASH_NAME_MAP.keys())


def memory_bound_hexdigest(
    hash_func: Optional[HashFunctionT] = None,
    hash_func_name: Optional[HashFunctionNameEnum] = None,
    path: Optional[str] = None,
    file=None,
):
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
        for block in iter(lambda: file.read(BLOCK_SIZE), b""):
            hasher.update(block)
        return hasher.hexdigest()
    finally:
        file.close()


def md5_hash_file(path: Union[str, os.PathLike]) -> Optional[str]:
    """
    Return a md5 hashdigest for a file or None if path could not be read.
    """
    hasher = hashlib.md5()
    try:
        with open(path, "rb") as afile:
            buf = afile.read()
            hasher.update(buf)
            return hasher.hexdigest()
    except OSError:
        # This may happen if path has been deleted
        return None


def new_secure_hash_v2(text_type: Union[bytes, str]) -> str:
    """More modern version of new_secure_hash.

    Certain passwords are set via new_insecure_hash (previously new_secure_hash),
    so that needs to remain for legacy purposes.
    """
    assert text_type is not None
    return sha512(smart_str(text_type)).hexdigest()


def new_insecure_hash(text_type: Union[bytes, str]) -> str:
    """Returns the hexdigest of the sha1 hash of the argument `text_type`.

    Previously called new_secure_hash, but this should not be considered
    secure - SHA1 is no longer considered a secure hash and has been broken
    since the early 2000s.

    use_pbkdf2 should be set by default and galaxy.security.passwords should
    be the default used for passwords in Galaxy.
    """
    assert text_type is not None
    return sha1(smart_str(text_type)).hexdigest()


def hmac_new(key: Union[bytes, str], value: Union[bytes, str]) -> str:
    return hmac.new(smart_str(key), smart_str(value), sha).hexdigest()


def is_hashable(value: Any) -> bool:
    try:
        hash(value)
    except Exception:
        return False
    return True


__all__ = ("md5", "hashlib", "sha1", "sha", "new_insecure_hash", "new_secure_hash_v2", "hmac_new", "is_hashable")
