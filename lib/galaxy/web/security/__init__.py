import os, os.path, logging

import pkg_resources
pkg_resources.require( "pycrypto" )

from Crypto.Cipher import Blowfish
from Crypto.Util.randpool import RandomPool
from Crypto.Util import number

log = logging.getLogger( __name__ )

if os.path.exists( "/dev/urandom" ):
    # We have urandom, use it as the source of random data
    random_fd = os.open( "/dev/urandom", os.O_RDONLY )
    def get_random_bytes( nbytes ):
        value = os.read( random_fd, nbytes )
        # Normally we should get as much as we need
        if len( value ) == nbytes:
            return value.encode( "hex" )
        # If we don't, keep reading (this is slow and should never happen)
        while len( value ) < nbytes:
            value += os.read( random_fd, nbytes - len( value ) )
        return value.encode( "hex" )
else:
    def get_random_bytes( nbytes ):
        nbits = nbytes * 8
        random_pool = RandomPool( 1064 )
        while random_pool.entropy < nbits:
            random_pool.add_event()
        random_pool.stir()
        return str( number.getRandomNumber( nbits, random_pool.get_bytes ) )

class SecurityHelper( object ):
    def __init__( self, **config ):
        self.id_secret = config['id_secret']
        self.id_cipher = Blowfish.new( self.id_secret )
    def encode_id( self, obj_id ):
        # Convert to string
        s = str( obj_id )
        # Pad to a multiple of 8 with leading "!" 
        s = ( "!" * ( 8 - len(s) % 8 ) ) + s
        # Encrypt
        return self.id_cipher.encrypt( s ).encode( 'hex' )
    def decode_id( self, obj_id ):
        return int( self.id_cipher.decrypt( obj_id.decode( 'hex' ) ).lstrip( "!" ) )
    def encode_guid( self, session_key ):
        # Session keys are strings
        # Pad to a multiple of 8 with leading "!" 
        s = ( "!" * ( 8 - len( session_key ) % 8 ) ) + session_key
        # Encrypt
        return self.id_cipher.encrypt( s ).encode( 'hex' )
    def decode_guid( self, session_key ):
        # Session keys are strings
        return self.id_cipher.decrypt( session_key.decode( 'hex' ) ).lstrip( "!" )
    def get_new_guid( self ):
        # Generate a unique, high entropy 128 bit random number
        return get_random_bytes( 16 )
