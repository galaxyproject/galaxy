""" Sourced from https://github.com/RomeoDespres/pkce/blob/master/pkce/__init__.py


MIT License

Copyright (c) 2020 Roméo Després

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

"""
import secrets
import hashlib
import base64
from typing import Tuple


def generate_code_verifier(length: int = 128) -> str:
    """Return a random PKCE-compliant code verifier.
    Parameters
    ----------
    length : int
        Code verifier length. Must verify `43 <= length <= 128`.
    Returns
    -------
    code_verifier : str
        Code verifier.
    Raises
    ------
    ValueError
        When `43 <= length <= 128` is not verified.
    """
    if not 43 <= length <= 128:
        msg = 'Parameter `length` must verify `43 <= length <= 128`.'
        raise ValueError(msg)
    code_verifier = secrets.token_urlsafe(96)[:length]
    return code_verifier


def generate_pkce_pair(code_verifier_length: int = 128) -> Tuple[str, str]:
    """Return random PKCE-compliant code verifier and code challenge.
    Parameters
    ----------
    code_verifier_length : int
        Code verifier length. Must verify
        `43 <= code_verifier_length <= 128`.
    Returns
    -------
    code_verifier : str
    code_challenge : str
    Raises
    ------
    ValueError
        When `43 <= code_verifier_length <= 128` is not verified.
    """
    if not 43 <= code_verifier_length <= 128:
        msg = 'Parameter `code_verifier_length` must verify '
        msg += '`43 <= code_verifier_length <= 128`.'
        raise ValueError(msg)
    code_verifier = generate_code_verifier(code_verifier_length)
    code_challenge = get_code_challenge(code_verifier)
    return code_verifier, code_challenge


def get_code_challenge(code_verifier: str) -> str:
    """Return the PKCE-compliant code challenge for a given verifier.
    Parameters
    ----------
    code_verifier : str
        Code verifier. Must verify `43 <= len(code_verifier) <= 128`.
    Returns
    -------
    code_challenge : str
        Code challenge that corresponds to the input code verifier.
    Raises
    ------
    ValueError
        When `43 <= len(code_verifier) <= 128` is not verified.
    """
    if not 43 <= len(code_verifier) <= 128:
        msg = 'Parameter `code_verifier` must verify '
        msg += '`43 <= len(code_verifier) <= 128`.'
        raise ValueError(msg)
    hashed = hashlib.sha256(code_verifier.encode('ascii')).digest()
    encoded = base64.urlsafe_b64encode(hashed)
    code_challenge = encoded.decode('ascii')[:-1]
    return code_challenge
