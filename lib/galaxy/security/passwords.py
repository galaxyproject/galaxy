import hmac
import hashlib
from struct import Struct
from operator import xor
from itertools import starmap
from os import urandom
from base64 import b64encode
from galaxy.util import safe_str_cmp

SALT_LENGTH = 12
KEY_LENGTH = 24
HASH_FUNCTION = 'sha256'
COST_FACTOR = 10000


def hash_password( password ):
    """
    Hash a password, currently will use the PBKDF2 scheme.
    """
    return hash_password_PBKDF2( password )


def check_password( guess, hashed ):
    """
    Check a hashed password. Supports either PBKDF2 if the hash is
    prefixed with that string, or sha1 otherwise.
    """
    if hashed.startswith( "PBKDF2" ):
        if check_password_PBKDF2( guess, hashed ):
            return True
    else:
        # Passwords were originally encoded with sha1 and hexed
        if hashlib.sha1( guess ).hexdigest() == hashed:
            return True
    # Password does not match
    return False


def hash_password_PBKDF2( password ):
    # Generate a random salt
    salt = b64encode( urandom( SALT_LENGTH ) )
    # Apply the pbkdf2 encoding
    hashed = pbkdf2_bin( bytes( password ), salt, COST_FACTOR, KEY_LENGTH, getattr( hashlib, HASH_FUNCTION ) )
    # Format
    return 'PBKDF2${0}${1}${2}${3}'.format( HASH_FUNCTION, COST_FACTOR, salt, b64encode( hashed ) )


def check_password_PBKDF2( guess, hashed ):
    # Split the database representation to extract cost_factor and salt
    name, hash_function, cost_factor, salt, encoded_original = hashed.split( '$', 5 )
    # Hash the guess using the same parameters
    hashed_guess = pbkdf2_bin( bytes( guess ), salt, int( cost_factor ), KEY_LENGTH, getattr( hashlib, hash_function ) )
    encoded_guess = b64encode( hashed_guess )
    return safe_str_cmp( encoded_original, encoded_guess )


# Taken from https://github.com/mitsuhiko/python-pbkdf2/blob/master/pbkdf2.py
# (c) Copyright 2011 by Armin Ronacher, BSD LICENSE
_pack_int = Struct('>I').pack


def pbkdf2_bin( data, salt, iterations=1000, keylen=24, hashfunc=None ):
    """Returns a binary digest for the PBKDF2 hash algorithm of `data`
    with the given `salt`.  It iterates `iterations` time and produces a
    key of `keylen` bytes.  By default SHA-1 is used as hash function,
    a different hashlib `hashfunc` can be provided.
    """
    hashfunc = hashfunc or hashlib.sha1
    mac = hmac.new(data, None, hashfunc)

    def _pseudorandom(x, mac=mac):
        h = mac.copy()
        h.update(x)
        return [ord(_) for _ in h.digest()]
    buf = []
    for block in range(1, -(-keylen // mac.digest_size) + 1):
        rv = u = _pseudorandom(salt + _pack_int(block))
        for i in range(iterations - 1):
            u = _pseudorandom(''.join(map(chr, u)))
            rv = starmap( xor, zip( rv, u ) )  # Python < 2.6.8: starmap requires function inputs to be tuples, so we need to use zip instead of izip
        buf.extend(rv)
    return ''.join(map(chr, buf))[:keylen]
