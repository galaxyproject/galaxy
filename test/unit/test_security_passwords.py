# -*- coding: utf-8 -*-

from galaxy.security import passwords


def test_hash_and_check():
    simple_pass = "my simple pass"
    complex_pass = u"à strange ünicode ڃtring"
    not_pass_simple = "not simple pass"
    not_pass_complex = u"à strange ün ڃtring"

    simple_pass_hash = passwords.hash_password(simple_pass)
    complex_pass_hash = passwords.hash_password(complex_pass)

    assert passwords.check_password(simple_pass, simple_pass_hash)
    assert passwords.check_password(complex_pass, complex_pass_hash)

    assert not passwords.check_password(complex_pass, simple_pass_hash)
    assert not passwords.check_password(not_pass_complex, simple_pass_hash)
    assert not passwords.check_password(not_pass_simple, simple_pass_hash)

    assert not passwords.check_password(simple_pass, complex_pass_hash)
    assert not passwords.check_password(not_pass_complex, complex_pass_hash)
    assert not passwords.check_password(not_pass_simple, complex_pass_hash)


def test_hash_consistent():
    # Make sure hashes created for earlier Galaxies continue to work in the future.
    simple_pass = "my simple pass"
    complex_pass = u"à strange ünicode ڃtring"

    # Check hashes built in Python 2 for 18.05.
    simple_pass_hash = 'PBKDF2$sha256$10000$LlkhoImT15LZAcFB$/afKJrFX9GXt6VEpB+omae19A2S4kBEY'
    complex_pass_hash = 'PBKDF2$sha256$10000$rg2gPThkJycziB0s$/BJ7AfuaYjpo5hhUvCMhf4TTrhsrOIH1'

    # Check hashes built in Python 3 for 18.05.
    simple_pass_hash_2 = 'PBKDF2$sha256$10000$vOIv7wGXS2/rGhDu$wS/5NwGSZm1ECv/vSEZb7jKjYSzXWZDL'
    complex_pass_hash_2 = 'PBKDF2$sha256$10000$q1av/Clyujm5Fdc6$Dh7o1KTMn/YQYc5NurN+aVaF3uaI8iOv'

    # Check older sha1 passwords that may still be the database as well.
    simple_pass_hash_old = '58f17339ffdb71050734d2fbdd41b870423fe433'
    complex_pass_hash_old = 'b567602039213afc0db026eedd72bd3ee2e57092'

    assert passwords.check_password(simple_pass, simple_pass_hash)
    assert passwords.check_password(complex_pass, complex_pass_hash)

    assert passwords.check_password(simple_pass, simple_pass_hash_2)
    assert passwords.check_password(complex_pass, complex_pass_hash_2)

    assert passwords.check_password(simple_pass, simple_pass_hash_old)
    assert passwords.check_password(complex_pass, complex_pass_hash_old)

    assert not passwords.check_password(complex_pass, simple_pass_hash_old)
    assert not passwords.check_password(simple_pass, complex_pass_hash_old)
