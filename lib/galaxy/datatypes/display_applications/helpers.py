import pkg_resources
pkg_resources.require( "pycrypto" )
from Crypto.Cipher import Blowfish

def encode_dataset_user( trans, dataset, user ):
    #encode dataset id as usual
    #encode user id using the dataset create time as the key
    dataset_hash = trans.security.encode_id( dataset.id )
    if user is None:
        user_id = 'None'
    else:
        user_id = str( user.id )
    # Pad to a multiple of 8 with leading "!" 
    user_id = ( "!" * ( 8 - len( user_id ) % 8 ) ) + user_id
    cipher = Blowfish.new( str( dataset.create_time ) )
    return dataset_hash, cipher.encrypt( user_id ).encode( 'hex' )

def decode_dataset_user( trans, dataset_hash, user_hash ):
    #decode dataset id as usual
    #decode user id using the dataset create time as the key
    dataset_id = trans.security.decode_id( dataset_hash )
    dataset = trans.sa_session.query( trans.app.model.HistoryDatasetAssociation ).get( dataset_id )
    assert dataset, "Bad Dataset id provided to decode_dataset_user"
    cipher = Blowfish.new( str( dataset.create_time ) )
    user_id = cipher.decrypt( user_hash.decode( 'hex' ) ).lstrip( "!" )
    if user_id =='None':
        user = None
    else:
        user = trans.sa_session.query( trans.app.model.User ).get( int( user_id ) )
        assert user, "A Bad user id was passed to decode_dataset_user"
    return dataset, user
