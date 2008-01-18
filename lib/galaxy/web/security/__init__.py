import pkg_resources
pkg_resources.require( "pycrypto" )

from Crypto.Cipher import Blowfish

class SecurityHelper( object ):
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