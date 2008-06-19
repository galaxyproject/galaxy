import pkg_resources
pkg_resources.require( "pycrypto" )

from Crypto.Cipher import Blowfish
from Crypto.Util.randpool import RandomPool
from Crypto.Util import number

class SecurityHelper( object ):
    # TODO: checking if histories/datasets are owned by the current user) will be moved here.
    def __init__( self, **config ):
        self.id_secret = config['id_secret']
        self.id_cipher = Blowfish.new( self.id_secret )
    def encode_id( self, id ):
        # Convert to string
        s = str( id )
        # Pad to a multiple of 8 with leading "!" 
        s = ( "!" * ( 8 - len(s) % 8 ) ) + s
        # Encrypt
        return self.id_cipher.encrypt( s ).encode( 'hex' )
    def decode_id( self, id ):
        return int( self.id_cipher.decrypt( id.decode( 'hex' ) ).lstrip( "!" ) )
    def encode_session_key( self, session_key ):
        # Session keys are strings
        # Pad to a multiple of 8 with leading "!" 
        s = ( "!" * ( 8 - len( session_key ) % 8 ) ) + session_key
        # Encrypt
        return self.id_cipher.encrypt( s ).encode( 'hex' )
    def decode_session_key( self, session_key ):
        # Session keys are strings
        return self.id_cipher.decrypt( session_key.decode( 'hex' ) ).lstrip( "!" )
    def get_new_session_key( self ):
        # Generate a unique, high entropy 128 bit random number
        random_pool = RandomPool( 16 )
        while random_pool.entropy < 128:
            random_pool.add_event()
        random_pool.stir()
        rn = number.getRandomNumber( 128, random_pool.get_bytes )
        # session_key must be a string
        return str( rn )
        