import hashlib
from base64 import b64encode
from os import urandom

from galaxy.util import (
    safe_str_cmp,
    smart_str,
    unicodify,
)

SALT_LENGTH = 12
KEY_LENGTH = 24
HASH_FUNCTION = "sha256"
COST_FACTOR = 100000


def hash_password(password):
    """
    Hash a password, currently will use the PBKDF2 scheme.
    """
    if password is None:
        raise Exception("password cannot be None")
    return hash_password_PBKDF2(password)


def check_password(guess, hashed):
    """
    Check a hashed password. Supports either PBKDF2 if the hash is
    prefixed with that string, or sha1 otherwise.
    """
    if hashed.startswith("PBKDF2"):
        if check_password_PBKDF2(guess, hashed):
            return True
    else:
        # Passwords were originally encoded with sha1 and hexed
        if safe_str_cmp(hashlib.sha1(smart_str(guess)).hexdigest(), hashed):
            return True
    # Password does not match
    return False


def hash_password_PBKDF2(password):
    # Generate a random salt
    salt = b64encode(urandom(SALT_LENGTH))
    # Apply the pbkdf2 encoding
    hashed_password = pbkdf2_bin(password, salt, COST_FACTOR, KEY_LENGTH, HASH_FUNCTION)
    encoded_password = unicodify(b64encode(hashed_password))
    # Format
    return f"PBKDF2${HASH_FUNCTION}${COST_FACTOR}${unicodify(salt)}${encoded_password}"


def check_password_PBKDF2(guess, hashed):
    # Split the database representation to extract cost_factor and salt
    name, hash_function, cost_factor, salt, encoded_original = hashed.split("$", 5)
    # Hash the guess using the same parameters
    hashed_guess = pbkdf2_bin(guess, salt, int(cost_factor), KEY_LENGTH, hash_function)
    encoded_guess = unicodify(b64encode(hashed_guess))
    return safe_str_cmp(encoded_original, encoded_guess)


def pbkdf2_bin(data, salt, iterations=COST_FACTOR, keylen=KEY_LENGTH, hashfunc=HASH_FUNCTION):
    """Returns a binary digest for the PBKDF2 hash algorithm of `data`
    with the given `salt`.  It iterates `iterations` time and produces a
    key of `keylen` bytes.  By default SHA-256 is used as hash function,
    a different hashlib `hashfunc` can be provided.
    """
    data = smart_str(data)
    salt = smart_str(salt)

    return hashlib.pbkdf2_hmac(hashfunc, data, salt, iterations, keylen)
