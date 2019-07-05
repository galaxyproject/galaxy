# -*- coding: utf-8 -*-

from galaxy.web import security


test_helper_1 = security.SecurityHelper(id_secret="secu1")
test_helper_2 = security.SecurityHelper(id_secret="secu2")


def test_maximum_length_handling_ascii():
    # Test that id secrets can be up to 56 characters long.
    longest_id_secret = "m" * security.MAXIMUM_ID_SECRET_LENGTH
    helper = security.SecurityHelper(id_secret=longest_id_secret)
    helper.encode_id(1)

    # Test that security helper will catch if the id secret is too long.
    threw_exception = False
    longer_id_secret = "m" * (security.MAXIMUM_ID_SECRET_LENGTH + 1)
    try:
        security.SecurityHelper(id_secret=longer_id_secret)
    except Exception:
        threw_exception = True

    assert threw_exception

    # Test that different kinds produce different keys even when id secret
    # is very long.
    e11 = helper.encode_id(1, kind="moo")
    e12 = helper.encode_id(1, kind="moo2")

    assert e11 != e12

    # Test that long kinds are rejected because it uses up "too much" randomness
    # from id_secret values. This isn't a strict requirement up but lets just enforce
    # the best practice.
    assertion_error_raised = False
    try:
        helper.encode_id(1, kind="this is a really long kind")
    except AssertionError:
        assertion_error_raised = True

    assert assertion_error_raised


def test_maximum_length_handling_nonascii():
    longest_id_secret = "◎◎◎◎◎◎◎◎◎◎◎◎◎◎◎◎◎◎"
    helper = security.SecurityHelper(id_secret=longest_id_secret)
    helper.encode_id(1)

    # Test that security helper will catch if the id secret is too long.
    threw_exception = False
    longer_id_secret = "◎◎◎◎◎◎◎◎◎◎◎◎◎◎◎◎◎◎◎"
    try:
        security.SecurityHelper(id_secret=longer_id_secret)
    except Exception:
        threw_exception = True

    assert threw_exception

    # Test that different kinds produce different keys even when id secret
    # is very long.
    e11 = helper.encode_id(1, kind="moo")
    e12 = helper.encode_id(1, kind="moo2")

    assert e11 != e12


def test_encode_decode():
    # Different ids are encoded differently
    assert test_helper_1.encode_id(1) != test_helper_1.encode_id(2)
    # But decoding and encoded id brings back to original id
    assert 1 == test_helper_1.decode_id(test_helper_1.encode_id(1))


def test_nested_encoding():
    # Does nothing if not a dict
    assert test_helper_1.encode_all_ids(1) == 1

    # Encodes top-level things ending in _id
    assert test_helper_1.encode_all_ids(dict(history_id=1))["history_id"] == test_helper_1.encode_id(1)
    # ..except tool_id
    assert test_helper_1.encode_all_ids(dict(tool_id=1))["tool_id"] == 1

    # Encodes lists at top level is end in _ids
    expected_ids = [test_helper_1.encode_id(1), test_helper_1.encode_id(2)]
    assert test_helper_1.encode_all_ids(dict(history_ids=[1, 2]))["history_ids"] == expected_ids

    # Encodes nested stuff if and only if recursive set to true.
    nested_dict = dict(objects=dict(history_ids=[1, 2]))
    assert test_helper_1.encode_all_ids(nested_dict)["objects"]["history_ids"] == [1, 2]
    assert test_helper_1.encode_all_ids(nested_dict, recursive=False)["objects"]["history_ids"] == [1, 2]
    assert test_helper_1.encode_all_ids(nested_dict, recursive=True)["objects"]["history_ids"] == expected_ids


def test_per_kind_encode_deocde():
    # Different ids are encoded differently
    assert test_helper_1.encode_id(1, kind="k1") != test_helper_1.encode_id(2, kind="k1")
    # But decoding and encoded id brings back to original id
    assert 1 == test_helper_1.decode_id(test_helper_1.encode_id(1, kind="k1"), kind="k1")


def test_different_secrets_encode_differently():
    assert test_helper_1.encode_id(1) != test_helper_2.encode_id(1)


def test_per_kind_encodes_id_differently():
    assert test_helper_1.encode_id(1) != test_helper_2.encode_id(1, kind="new_kind")


def test_encode_dict():
    test_dict = dict(
        id=1,
        other=2,
        history_id=3,
    )
    encoded_dict = test_helper_1.encode_dict_ids(test_dict)
    assert encoded_dict["id"] == test_helper_1.encode_id(1)
    assert encoded_dict["other"] == 2
    assert encoded_dict["history_id"] == test_helper_1.encode_id(3)


def test_guid_generation():
    guids = set()
    for i in range(100):
        guids.add(test_helper_1.get_new_guid())
    assert len(guids) == 100  # Not duplicate guids generated.


def test_encode_decode_guid():
    session_key = test_helper_1.get_new_guid()
    encoded_key = test_helper_1.encode_guid(session_key)
    decoded_key = test_helper_1.decode_guid(encoded_key)
    assert session_key == decoded_key, "%s != %s" % (session_key, decoded_key)
