from galaxy.web import security


test_helper_1 = security.SecurityHelper( id_secret="sec1" )
test_helper_2 = security.SecurityHelper( id_secret="sec2" )


def test_encode_decode():
    # Different ids are encoded differently
    assert test_helper_1.encode_id( 1 ) != test_helper_1.encode_id( 2 )
    # But decoding and encoded id brings back to original id
    assert 1 == test_helper_1.decode_id( test_helper_1.encode_id( 1 ) )


def test_nested_encoding():
    # Does nothing if not a dict
    assert test_helper_1.encode_all_ids( 1 ) == 1

    # Encodes top-level things ending in _id
    assert test_helper_1.encode_all_ids( dict( history_id=1 ) )[ "history_id" ] == test_helper_1.encode_id( 1 )
    # ..except tool_id
    assert test_helper_1.encode_all_ids( dict( tool_id=1 ) )[ "tool_id" ] == 1

    # Encodes lists at top level is end in _ids
    expected_ids = [ test_helper_1.encode_id( 1 ), test_helper_1.encode_id( 2 ) ]
    assert test_helper_1.encode_all_ids( dict( history_ids=[ 1, 2 ] ) )[ "history_ids" ] == expected_ids

    # Encodes nested stuff if and only if recursive set to true.
    nested_dict = dict( objects=dict( history_ids=[ 1, 2 ] ) )
    assert test_helper_1.encode_all_ids( nested_dict )[ "objects" ][ "history_ids" ] == [ 1, 2 ]
    assert test_helper_1.encode_all_ids( nested_dict, recursive=False )[ "objects" ][ "history_ids" ] == [ 1, 2 ]
    assert test_helper_1.encode_all_ids( nested_dict, recursive=True )[ "objects" ][ "history_ids" ] == expected_ids


def test_per_kind_encode_deocde():
    # Different ids are encoded differently
    assert test_helper_1.encode_id( 1, kind="k1" ) != test_helper_1.encode_id( 2, kind="k1" )
    # But decoding and encoded id brings back to original id
    assert 1 == test_helper_1.decode_id( test_helper_1.encode_id( 1, kind="k1" ), kind="k1" )


def test_different_secrets_encode_differently():
    assert test_helper_1.encode_id( 1 ) != test_helper_2.encode_id( 1 )


def test_per_kind_encodes_id_differently():
    assert test_helper_1.encode_id( 1 ) != test_helper_2.encode_id( 1, kind="new_kind" )


def test_encode_dict():
    test_dict = dict(
        id=1,
        other=2,
        history_id=3,
    )
    encoded_dict = test_helper_1.encode_dict_ids( test_dict )
    assert encoded_dict[ "id" ] == test_helper_1.encode_id( 1 )
    assert encoded_dict[ "other" ] == 2
    assert encoded_dict[ "history_id" ] == test_helper_1.encode_id( 3 )


def test_guid_generation():
    guids = set()
    for i in range( 100 ):
        guids.add( test_helper_1.get_new_guid() )
    assert len( guids ) == 100  # Not duplicate guids generated.


def test_encode_decode_guid():
    session_key = test_helper_1.get_new_guid()
    encoded_key = test_helper_1.encode_guid( session_key )
    decoded_key = test_helper_1.decode_guid( encoded_key ).encode( "utf-8" )
    assert session_key == decoded_key, "%s != %s" % ( session_key, decoded_key )
